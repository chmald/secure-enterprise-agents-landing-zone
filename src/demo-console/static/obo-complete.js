"use strict";
if (window.opener) window.opener.postMessage({ type: "demo-obo-complete" }, window.location.origin);
window.close();
