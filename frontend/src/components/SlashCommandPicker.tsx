/* SlashCommandPicker.tsx — slash-command panel + chip input for the chat bar.
   Ported from ui_kits/math-coach/slash-command-picker.jsx.
   Styles live in styles/pages.css under "SLASH COMMAND PICKER". */
import { useState, useRef, useMemo, useEffect, forwardRef, useImperativeHandle } from "react";
import type { ReactNode } from "react";
import { Icons } from "../lib/icons";
import type { IconName } from "../lib/icons";

const SLASH_COMMANDS = [
  { id: "generate", template: "/generate", arg: "brief",   icon: "spark" as IconName, desc: "Create a fresh mock exam from your prompt", chipMode: true  },
  { id: "exam",     template: "/exam",     arg: "session", icon: "exam"  as IconName, desc: "Load an official past-exam session by year",  chipMode: false },
  { id: "retrieve", template: "/retrieve", arg: "topic",   icon: "book"  as IconName, desc: "Pull textbook pages and past questions",       chipMode: true  },
] as const;

type SlashCommand = typeof SLASH_COMMANDS[number];

export interface SlashSendPayload {
  command: string | null;
  arg: string | null;
  text: string;
}

export interface SlashCommandPickerHandle {
  setValue: (text: string) => void;
}

interface Props {
  onSelect?: (command: string) => void;
  onSend?: (payload: SlashSendPayload) => void;
  placeholder?: string;
  disabled?: boolean;
  onChipChange?: (command: string | null) => void;
  adornment?: ReactNode;
}

export const SlashCommandPicker = forwardRef<SlashCommandPickerHandle, Props>(
  function SlashCommandPicker(
    {
      onSelect,
      onSend,
      placeholder = "Type / for a command, or ask the coach…",
      disabled = false,
      onChipChange,
      adornment,
    },
    ref
  ) {
    const [chip, setChip] = useState<SlashCommand | null>(null);
    const [raw, setRaw] = useState("");
    const [arg, setArg] = useState("");
    const [active, setActive] = useState(0);
    const taRef = useRef<HTMLTextAreaElement>(null);

    // query is non-null only when no chip is set and raw starts with "/"
    const query = !chip && raw.startsWith("/") ? raw.slice(1) : null;
    const matches = useMemo(() => {
      if (query == null || /\s/.test(query)) return [];
      const q = query.toLowerCase();
      return SLASH_COMMANDS.filter((c) => c.id.startsWith(q));
    }, [query]);
    const open = matches.length > 0;

    // Reset highlighted row when the query changes
    useEffect(() => { setActive(0); }, [query]);

    // Notify parent whenever the active chip command changes
    useEffect(() => {
      onChipChange?.(chip ? chip.template : null);
    }, [chip, onChipChange]);

    // Auto-grow the textarea
    useEffect(() => {
      const el = taRef.current;
      if (!el) return;
      el.style.height = "auto";
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }, [raw, arg]);

    useImperativeHandle(ref, () => ({
      setValue(text: string) {
        setChip(null);
        setRaw(text);
        setArg("");
        requestAnimationFrame(() => taRef.current?.focus());
      },
    }));

    const focusField = () => requestAnimationFrame(() => taRef.current?.focus());

    const choose = (cmd: SlashCommand) => {
      setRaw("");
      onSelect?.(cmd.template);
      if (cmd.chipMode) {
        setChip(cmd);
        setArg("");
        focusField();
      } else {
        // Non-chip commands (e.g. /exam) fire onSelect and reset
        setChip(null);
        setArg("");
        focusField();
      }
    };

    const removeChip = () => {
      setChip(null);
      setRaw("");
      setArg("");
      focusField();
    };

    const submit = () => {
      if (chip) {
        const a = arg.trim();
        onSend?.({ command: chip.template, arg: a, text: `${chip.template} ${a}`.trim() });
        setChip(null);
        setArg("");
      } else {
        const t = raw.trim();
        if (!t) return;
        onSend?.({ command: null, arg: null, text: t });
        setRaw("");
      }
    };

    const onChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      chip ? setArg(e.target.value) : setRaw(e.target.value);
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (open) {
        if (e.key === "ArrowDown") { e.preventDefault(); setActive((i) => (i + 1) % matches.length); return; }
        if (e.key === "ArrowUp")   { e.preventDefault(); setActive((i) => (i - 1 + matches.length) % matches.length); return; }
        if (e.key === "Enter")     { e.preventDefault(); choose(matches[active]); return; }
        if (e.key === "Tab")       { e.preventDefault(); choose(matches[active]); return; }
        if (e.key === "Escape")    { e.preventDefault(); setRaw(""); return; }
      }
      if (e.key === "Backspace" && chip && arg === "" && e.currentTarget.selectionStart === 0) {
        e.preventDefault();
        removeChip();
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
    };

    const value = chip ? arg : raw;
    const canSend = chip ? true : !!raw.trim();
    const ph = chip ? `Enter ${chip.arg}…` : placeholder;

    const SendIcon = Icons.send;

    return (
      <div className="slash-host">
        <div className={`slash-stack${open ? " is-open" : ""}`}>
          {open && (
            <div className="slash-panel" role="listbox" aria-label="Slash commands">
              <div className="slash-head">
                <span className="lbl">Commands</span>
                <span className="q">{raw}</span>
              </div>
              <div className="slash-list">
                {matches.map((c, i) => {
                  const CmdIcon = Icons[c.icon];
                  return (
                    <div
                      key={c.id}
                      role="option"
                      aria-selected={i === active}
                      className={`slash-row${i === active ? " is-active" : ""}`}
                      onMouseEnter={() => setActive(i)}
                      onMouseDown={(e) => { e.preventDefault(); choose(c); }}
                    >
                      <span className="slash-ico"><CmdIcon size={16} className="" /></span>
                      <div className="slash-text">
                        <div className="slash-cmd">{c.template} <span className="arg">[{c.arg}]</span></div>
                        <div className="slash-desc">{c.desc}</div>
                      </div>
                      <span className="slash-enter"><span className="slash-kbd">↵</span> use</span>
                    </div>
                  );
                })}
              </div>
              <div className="slash-foot">
                <span><span className="slash-kbd">↑</span><span className="slash-kbd">↓</span> navigate</span>
                <span><span className="slash-kbd">↵</span> select</span>
                <span><span className="slash-kbd">esc</span> dismiss</span>
              </div>
            </div>
          )}

          <div className="slash-input">
            <div className="slash-field">
              {chip && (
                <span className="slash-chip">
                  <span className="slash-chip-ico">
                    {(() => { const I = Icons[chip.icon]; return <I size={13} className="" />; })()}
                  </span>
                  <span className="slash-chip-cmd">{chip.template}</span>
                  <button
                    type="button"
                    className="slash-chip-x"
                    aria-label="Remove command"
                    onMouseDown={(e) => { e.preventDefault(); removeChip(); }}
                  >×</button>
                </span>
              )}
              {adornment}
              <textarea
                ref={taRef}
                rows={1}
                placeholder={ph}
                value={value}
                onChange={onChange}
                onKeyDown={onKeyDown}
                disabled={disabled}
              />
            </div>
            <button
              className="slash-send"
              disabled={!canSend || disabled}
              onClick={submit}
              aria-label="Send"
            >
              <SendIcon size={18} className="" />
            </button>
          </div>
        </div>
      </div>
    );
  }
);
