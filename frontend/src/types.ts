/* Shared routing types for the app shell and pages. */

export type PageId =
  | "dashboard" | "exam" | "topics" | "chat" | "results" | "books";

export interface PageProps {
  navigate: (id: PageId) => void;
}
