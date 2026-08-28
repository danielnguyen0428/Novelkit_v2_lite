import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { I18nProvider } from "./i18n/I18nProvider";
import { router } from "./router";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
      <RouterProvider router={router} />
    </I18nProvider>
  </React.StrictMode>,
);
