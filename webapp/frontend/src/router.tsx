import { createBrowserRouter, redirect } from "react-router-dom";

export const router = createBrowserRouter([
  {
    path: "/",
    loader: () => redirect("/studio"),
  },
  {
    path: "/studio",
    lazy: async () => {
      const { StudioPage } = await import("./pages/StudioPage");
      return { Component: StudioPage };
    },
  },
]);
