import React from 'react';
import Header from '../components/Header/Header';

interface PageWrapperProps {
  children: string | JSX.Element | JSX.Element[] | (() => JSX.Element);
}

const links = [
  { label: 'Home', url: '/' },
  { label: 'Products', url: '/products' },
  { label: 'Login', url: '/login' },
];

const PageWrapper = (props: PageWrapperProps) => (
  <>
    <div className="sticky top-0">
      <Header links={links} />
    </div>
    <div className="flex flex-col items-center justify-center p-4 h-full">
      {props.children}
    </div>
  </>
);

export default PageWrapper;
