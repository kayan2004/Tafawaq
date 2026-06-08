/* Shared routing types for the app shell and pages. */

export type PageId =
  | "dashboard" | "exam" | "past" | "topics" | "chat" | "history" | "results";

export interface PageProps {
  navigate: (id: PageId) => void;
}
