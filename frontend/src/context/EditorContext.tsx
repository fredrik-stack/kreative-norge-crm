import { createContext, useContext } from "react";
import type { EditorData } from "../hooks/useEditorData";

const EditorContext = createContext<EditorData | null>(null);

export function EditorProvider(props: { value: EditorData; children: React.ReactNode }) {
  return <EditorContext.Provider value={props.value}>{props.children}</EditorContext.Provider>;
}

export function useEditor(): EditorData {
  const value = useContext(EditorContext);
  if (!value) {
    throw new Error("useEditor must be used within EditorProvider");
  }
  return value;
}
