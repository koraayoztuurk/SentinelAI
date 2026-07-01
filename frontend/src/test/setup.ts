// Vitest setup: jest-dom matchers.
//
// MSW powers the development browser demo (see `main.tsx`). In the jsdom test
// environment MSW's node request interception is unreliable on this runtime, so the
// page integration tests mock the communication layer directly instead; the mapper
// test exercises the same sample data without the network.

import "@testing-library/jest-dom/vitest";
