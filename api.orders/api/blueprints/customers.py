from flask import Blueprint, request
from api.models import Customer
from api.schemas import CustomerSchema
import jwt
import os
from dotenv import load_dotenv
from logger import logger
from datetime import datetime, timedelta
import pytz


load_dotenv()


SECRET_KEY = os.environ.get("SECRET_KEY") or "this is a secret"
customers_blueprint = Blueprint("customers_blueprint", __name__)
customer_schema = CustomerSchema()


@customers_blueprint.route("/register", methods=["POST"])
def add_user():
    try:
        json_data = request.get_json()

        if not json_data:
            return {
                "message": "Please provide user details",
                "data": None,
                "error": "Bad request",
            }, 400
        validated = customer_schema.load(json_data)
        if not validated:
            return dict(message="Invalid data", data=None, error=validated), 400
        try:
            user_exist = Customer.get(CustomerEmail=validated.get("CustomerEmail"))
        except Customer.DoesNotExist:
            user_exist = None
        if user_exist:
            return {
                "message": "User already exists",
                # "error": "User already exists",
                "data": None,
            }, 409
        customer = Customer.create(**validated)
        user = customer_schema.dump(customer)
        return {"message": "Successfully created new user", "data": user}, 201
    except Exception as e:
        logger.error(str(e))
        return {"message": "Something went wrong", "error": str(e), "data": None}, 500


@customers_blueprint.route("/login", methods=["POST"])
def update_product_status():
    json_data = request.get_json()
    if not json_data:
        return {"message": "No details provided"}, 400
    try:
        user = customer_schema.load(json_data)
        customer, error = Customer.validate_login(
            user["CustomerEmail"], user["CustomerPassword"]
        )
        if error:
            return {"message": error}, 400
        customer = customer_schema.dump(customer)
        expiration_time = datetime.now(pytz.timezone("US/Eastern")) + timedelta(hours=1)
        customer["token"] = jwt.encode(
            {"user_id": customer["CustomerID"], "exp": expiration_time},
            SECRET_KEY,
            algorithm="HS256",
        )
        return {"data": customer, "message": "Login Succesfull"}, 200
    except Exception as e:
        logger.error(e)
        return {"message": e}, 400
