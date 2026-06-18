import { useEffect, useState } from "react";
import {
  listPastExamFiles, triggerPastExamIngestion, type PastExamFile,
  listTextbookChapters, triggerTextbookIngestion, type TextbookChapter,
  parseSseEvents, type IngestionEvent,
} from "../lib/api";
import Tabs from "../components/Tabs";
import Button from "../components/Button";
import Card from "../components/Card";
import Modal from "../components/Modal";
import JobPanel, { type FileJob } from "../components/JobPanel";
import { StatusBadge } from "../components/Badge";
import Skeleton from "../components/Skeleton";
import EmptyState from "../components/EmptyState";
import { Icons } from "../lib/icons";

const PAST_EXAM_STAGES = ["Extract", "Chunk", "Tag", "Embed", "Done"];
const TEXTBOOK_STAGES = ["Parse", "Done"];

type Tab = "Past Exams" | "Textbook";

async function consumeStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (evt: IngestionEvent) => void,
) {
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSseEvents(buffer);
    buffer = rest;
    events.forEach(onEvent);
  }
}

export default function Ingestion({ token }: { token: string }) {
  const [tab, setTab] = useState<Tab>("Past Exams");
  const [files, setFiles] = useState<PastExamFile[] | null>(null);
  const [chapters, setChapters] = useState<TextbookChapter[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkConfirmOpen, setBulkConfirmOpen] = useState(false);
  const [reingestTarget, setReingestTarget] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [pendingUploads, setPendingUploads] = useState<File[]>([]);
  const [jobOpen, setJobOpen] = useState(false);
  const [jobs, setJobs] = useState<FileJob[]>([]);
  const [jobStages, setJobStages] = useState<string[]>(PAST_EXAM_STAGES);

  function refetchFiles() {
    void listPastExamFiles(token).then(setFiles);
  }
  function refetchChapters() {
    void listTextbookChapters(token).then(setChapters);
  }

  useEffect(() => {
    void listPastExamFiles(token).then(setFiles);
    void listTextbookChapters(token).then(setChapters);
  }, [token]);

  function toggleSelect(filename: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(filename)) next.delete(filename);
      else next.add(filename);
      return next;
    });
  }

  function applyEvent(evt: IngestionEvent) {
    if (evt.event === "file_progress" && evt.file) {
      setJobs((prev) =>
        prev.map((j) =>
          j.filename === evt.file
            ? { ...j, stage: evt.stage ?? j.stage, chunks: evt.chunks ?? j.chunks, pages: evt.pages ?? j.pages }
            : j,
        ),
      );
    } else if (evt.event === "file_failed" && evt.file) {
      setJobs((prev) => prev.map((j) => (j.filename === evt.file ? { ...j, failed: true, error: evt.error } : j)));
    }
  }

  async function runPastExamIngestion(filenames: string[]) {
    setJobStages(PAST_EXAM_STAGES);
    setJobs(filenames.map((f) => ({ filename: f, stage: "pending", failed: false })));
    setJobOpen(true);
    const controller = new AbortController();
    const reader = await triggerPastExamIngestion(token, filenames, controller.signal);
    await consumeStream(reader, applyEvent);
    refetchFiles();
  }

  async function runTextbookIngestion(uploadFiles: File[]) {
    setJobStages(TEXTBOOK_STAGES);
    setJobs(uploadFiles.map((f) => ({ filename: f.name, stage: "pending", failed: false })));
    setJobOpen(true);
    const controller = new AbortController();
    const reader = await triggerTextbookIngestion(token, uploadFiles, controller.signal);
    await consumeStream(reader, applyEvent);
    refetchChapters();
  }

  function openBulkConfirm() {
    if (selected.size === 0) return;
    setBulkConfirmOpen(true);
  }

  function confirmBulk() {
    setBulkConfirmOpen(false);
    const names = Array.from(selected);
    setSelected(new Set());
    void runPastExamIngestion(names);
  }

  function confirmReingest() {
    if (!reingestTarget) return;
    const name = reingestTarget;
    setReingestTarget(null);
    void runPastExamIngestion([name]);
  }

  function confirmUpload() {
    setUploadOpen(false);
    const uploads = pendingUploads;
    setPendingUploads([]);
    void runTextbookIngestion(uploads);
  }

  const selectableFiles = files?.filter((f) => !f.parse_error) ?? [];

  return (
    <div>
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[20px] font-extrabold tracking-[-0.02em]">Content ingestion</h1>
          <p className="mt-1 text-[13px] font-medium" style={{ color: "var(--text-muted)" }}>
            Lebanese GS Grade 12 Mathematics — past exams and textbook chapters.
          </p>
        </div>
        {tab === "Past Exams" ? (
          <Button variant="primary" disabled={selected.size === 0} onClick={openBulkConfirm}>
            Ingest selected
          </Button>
        ) : (
          <Button variant="primary" onClick={() => setUploadOpen(true)}>Add .md files</Button>
        )}
      </div>

      <div className="mt-4">
        <Tabs tabs={["Past Exams", "Textbook"]} active={tab} onChange={(t) => setTab(t as Tab)} />
      </div>

      {tab === "Past Exams" && (
        <Card className="mt-4">
          {!files ? (
            <div className="flex flex-col gap-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9" />)}
            </div>
          ) : files.length === 0 ? (
            <EmptyState icon="file" heading="No PDF files found" body="Place exam PDFs in Math_GS_Exams_English/ on the API host." />
          ) : (
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="w-10 px-4 py-2.5" style={{ borderBottom: "1px solid var(--line)" }}>
                    <input
                      type="checkbox"
                      checked={selected.size > 0 && selected.size === selectableFiles.length}
                      onChange={(e) =>
                        setSelected(e.target.checked ? new Set(selectableFiles.map((f) => f.filename)) : new Set())
                      }
                    />
                  </th>
                  {["File", "Year", "Session", "Status", "Chunks", "Actions"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2.5 text-left text-[11px] font-bold uppercase tracking-[0.07em]"
                      style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--line)" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.filename}>
                    <td className="px-4 py-3" style={{ borderTop: "1px solid var(--line)" }}>
                      {!f.parse_error && (
                        <input type="checkbox" checked={selected.has(f.filename)} onChange={() => toggleSelect(f.filename)} />
                      )}
                    </td>
                    <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)" }}>
                      {f.filename}
                    </td>
                    <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>{f.year ?? "—"}</td>
                    <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>{f.session ?? "—"}</td>
                    <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>
                      <StatusBadge status={f.parse_error ? "failed" : f.ingested ? "ingested" : "not-ingested"} />
                    </td>
                    <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)", fontFamily: "var(--font-mono)" }}>
                      {f.chunk_count}
                    </td>
                    <td className="px-4 py-3 text-[13px]" style={{ borderTop: "1px solid var(--line)" }}>
                      {f.parse_error ? (
                        <span style={{ color: "var(--text-faint)" }}>Unrecognised filename</span>
                      ) : f.ingested ? (
                        <button
                          onClick={() => setReingestTarget(f.filename)}
                          className="text-[12px] font-semibold"
                          style={{ color: "var(--text-2)" }}
                        >
                          Re-ingest
                        </button>
                      ) : (
                        <button
                          onClick={() => void runPastExamIngestion([f.filename])}
                          className="rounded-[5px] border px-2.5 py-1 text-[12px]"
                          style={{ borderColor: "var(--line-strong)" }}
                        >
                          Ingest
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === "Textbook" && (
        <Card className="mt-4">
          {!chapters ? (
            <div className="flex flex-col gap-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : chapters.length === 0 ? (
            <EmptyState icon="book" heading="No textbook pages ingested yet" body="Upload markdown chapter files to populate the textbook." />
          ) : (
            <div className="flex flex-col">
              {chapters.map((c) => (
                <div key={c.chapter} className="flex items-center gap-3 px-4 py-3" style={{ borderTop: "1px solid var(--line)" }}>
                  <div
                    className="flex h-[30px] w-[30px] items-center justify-center rounded-md"
                    style={{ background: "var(--surface-2)", color: "var(--text-2)" }}
                  >
                    <Icons.book size={15} />
                  </div>
                  <div className="flex-1">
                    <div className="text-[13.5px] font-semibold">{c.chapter}</div>
                    <div className="text-[12px]" style={{ color: "var(--text-muted)" }}>
                      {c.page_count} pages (p. {c.min_page}–{c.max_page})
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      <Modal
        open={bulkConfirmOpen}
        title={`Ingest ${selected.size} file(s)?`}
        body="This runs the Extract → Chunk → Tag → Embed pipeline and calls paid Anthropic and Voyage AI APIs for each file."
        confirmLabel="Ingest selected"
        tone="warning"
        onConfirm={confirmBulk}
        onClose={() => setBulkConfirmOpen(false)}
      />

      <Modal
        open={reingestTarget !== null}
        title="Re-ingest this file?"
        body="Existing chunks for this file will be overwritten and paid APIs are called again."
        confirmLabel="Re-ingest and overwrite"
        tone="danger"
        onConfirm={confirmReingest}
        onClose={() => setReingestTarget(null)}
      />

      <Modal
        open={uploadOpen}
        title="Add .md files"
        body={
          <div>
            <p>
              Upload Lebanese GS Math textbook chapter files in markdown with YAML frontmatter
              (page, chapter, section, type), separated by ===PAGE_BREAK===.
            </p>
            <input
              type="file"
              multiple
              accept=".md"
              className="mt-3 text-[12.5px]"
              onChange={(e) => setPendingUploads(Array.from(e.target.files ?? []))}
            />
          </div>
        }
        confirmLabel="Ingest"
        tone="warning"
        confirmDisabled={pendingUploads.length === 0}
        onConfirm={confirmUpload}
        onClose={() => {
          setUploadOpen(false);
          setPendingUploads([]);
        }}
      />

      <JobPanel open={jobOpen} stageLabels={jobStages} jobs={jobs} onClose={() => setJobOpen(false)} />
    </div>
  );
}
