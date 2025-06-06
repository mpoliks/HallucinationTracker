//import Script from "next/script";
import Bank from "./bank";

export default function Home() {
  return (
    <>
      {/* <!-- Google tag (gtag.js) --> */}
      {/* <Script
        strategy="lazyOnload"
        async
        src="YOUR GOOGLE_ANALYTICS_SCRIPT_URL"
      ></Script>
      <Script strategy="lazyOnload">
        {`YOUR GOOGLE_ANALYTICS_TRACKING_CODE`}
      </Script> */}

      <Bank />
    </>
  );
}
