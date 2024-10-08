from flask import Blueprint, request
from marshmallow import ValidationError
from api.models import Orders, Activity
from api.schemas import OrderSchema
from datetime import datetime
import pytz
from logger import logger
from api.auth_middleware import token_required

orders_blueprint = Blueprint("orders_blueprint", __name__)


@orders_blueprint.route("/", methods=["GET"])
@token_required
def get_all_orders(current_user):
    order_schema = OrderSchema(many=True)
    try:
        orders = Orders.select().dicts()
        orders_serialized = order_schema.dump(orders)
    except Exception as err:
        logger.error(f"Error in get_all_orders: {err}")
        return {"data": [], "message": str(err)}, 500
    return {"data": orders_serialized, "message": "Retrieval Successful"}, 200


@orders_blueprint.route("/inpipeline", methods=["GET"])
@token_required
def get_inprogress_orders(current_user):
    order_schema = OrderSchema(many=True)

    try:
        orders = (
            Orders.select()
            .where(
                (Orders.OrderStatus == "Queued")
                | (Orders.OrderStatus == "InProgress")
                | (Orders.OrderStatus == "QA")
            )
            .order_by(Orders.OrderDate.desc())
            .limit(100)
            .dicts()
        )
        orders_serialized = order_schema.dump(orders)
        return {"data": orders_serialized, "message": "Order retrieval successful"}, 200
    except Exception as err:
        logger.error(f"Error in get_inprogress_orders: {err}")
        return {"data": [], "message": str(err)}, 500


@orders_blueprint.route("/pickerinpipeline", methods=["GET"])
@token_required
def get_pickerinprogress_orders(current_user):
    order_schema = OrderSchema(many=True)
    # user = request.args.get("user")
    try:
        orders = (
            Orders.select()
            .where(
                ((Orders.OrderStatus == "InProgress") | (Orders.OrderStatus == "QA"))
                & (Orders.TreatedBy == current_user.get("CustomerEmail"))
            )
            .dicts()
        )
        orders_serialized = order_schema.dump(orders)
        return {"data": orders_serialized, "message": "Order retrieval successful"}, 200
    except Exception as err:
        logger.error(f"Error in get_pickerinprogress_orders: {err}")
        return {"data": [], "message": str(err)}, 500


@orders_blueprint.route("/update_status", methods=["PUT"])
@token_required
def post_update_order_status(current_user):
    order_schema = OrderSchema()
    json_data = request.get_json()
    if not json_data:
        return {"message": "No order data provided!"}, 400

    try:
        order = order_schema.load(json_data)
        Orders.update(**order).where(Orders.OrderID == order["OrderID"]).execute()
        
        if order["OrderStatus"] == "InProgress":
            Activity.create(
                OrderID=order["OrderID"],
                Staff=current_user.get("CustomerID"),
                StartTime=datetime.now(pytz.timezone("US/Eastern")),
            )
        elif order["OrderStatus"] == "QA":
            activity = Activity.get(Activity.OrderID == order["OrderID"])
            try:
                
                if activity.StartTime:
                    Activity.update(
                        EndTime=datetime.now(pytz.timezone("US/Eastern")),
                        QAStart=datetime.now(pytz.timezone("US/Eastern"))
                    ).where(Activity.OrderID == order["OrderID"]).execute()

                    Activity.update_end_time_and_duration(
                        activity_id=activity.ActivityID
                    )
                else:
                    logger.info(
                        f"StartTime is missing for Activity with OrderID: {order['OrderID']}"
                    )
            except Activity.DoesNotExist:
                logger.error(f"Activity not found for OrderID: {order['OrderID']}")
            except Exception as e:
                logger.error(f"Error handling 'QA' status: {e}")
        elif order["OrderStatus"] == "Queued":

            Activity.delete().where(
                (Activity.OrderID == order["OrderID"])
                & (Activity.Staff == current_user.get("CustomerID"))
            ).execute()
        elif order["OrderStatus"] in ["Cancelled", "Complete"]:
            activity = Activity.get(Activity.OrderID == order["OrderID"])
            Activity.update(CheckedBy=current_user.get("CustomerID"),
                QAEnd=datetime.now(pytz.timezone("US/Eastern"))).where(
                Activity.OrderID == order["OrderID"]
            ).execute()
            Activity.update_end_time_and_duration(
                activity_id=activity.ActivityID
            )

    except ValidationError as err:
        logger.error(f"Error in post_update_order_status: {err}")
        return {"message": err.messages}, 422
    except Exception as err:
        logger.error(err)
        return {"message": str(err)}, 500
    return {
        "message": f'{order["OrderID"]} updated successfully!',
    }, 200
