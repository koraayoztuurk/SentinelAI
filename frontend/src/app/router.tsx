// Application routing.
//
// Business routes are introduced incrementally. The foundation (ES-023) shipped a
// single placeholder; ES-024 added the per-investigation dashboard route; ES-025
// adds the investigation workspace route.

import { createBrowserRouter } from "react-router-dom";
import { MainLayout } from "../layouts/MainLayout";
import { HomePage } from "../pages/HomePage";
import { InvestigationDashboardPage } from "../pages/InvestigationDashboardPage";
import { InvestigationWorkspacePage } from "../pages/InvestigationWorkspacePage";

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
  {
    path: "/investigations/:id/workspace",
    element: (
      <MainLayout>
        <InvestigationWorkspacePage />
      </MainLayout>
    ),
  },
]);
