// Application routing.
//
// Business routes are introduced incrementally. The foundation (ES-023) shipped a
// single placeholder; ES-024 adds the per-investigation dashboard route.

import { createBrowserRouter } from "react-router-dom";
import { MainLayout } from "../layouts/MainLayout";
import { HomePage } from "../pages/HomePage";
import { InvestigationDashboardPage } from "../pages/InvestigationDashboardPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <MainLayout>
        <HomePage />
      </MainLayout>
    ),
  },
  {
    path: "/investigations/:id",
    element: (
      <MainLayout>
        <InvestigationDashboardPage />
      </MainLayout>
    ),
  },
]);
