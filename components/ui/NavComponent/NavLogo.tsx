import React from "react";
import { useRouter } from "next/router";

const NavLogo = ({ srcHref, altText }: { srcHref?: string; altText?: string }) => {
  const router = useRouter();
  function goHome() {
    router.push("/");
  }
  return (
    <div className="ml-2 sm:ml-8 flex cursor-pointer" id="navbar-logo" onClick={() => goHome()} title= "Go Home">
      {srcHref ? (
        <img src={srcHref} alt={`${altText ? altText : "industry"} logo`} className="h-10 pr-2" />
      ) : (
        <img src="ldLogo/ld-logo.svg" alt="Default logo" className="h-10 pr-2" />
      )}
    </div>
  );
};

export default NavLogo;
