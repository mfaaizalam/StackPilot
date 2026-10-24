import { useMatch } from "react-router-dom";
import { useBoards } from "../api/queries.js";

// Current project: from the URL inside a project, otherwise the last one used.
export default function useActiveBoardId() {
  const match = useMatch("/boards/:boardId/*");
  const { data: boards = [] } = useBoards();
  const urlId = match?.params?.boardId;

  let boardId = urlId ?? null;
  if (!boardId) {
    const stored = localStorage.getItem("lastBoardId");
    if (stored && (boards.length === 0 || boards.some((b) => String(b.id) === stored))) {
      boardId = stored;
    } else if (boards[0]) {
      boardId = String(boards[0].id);
    }
  }
  const board = boards.find((b) => String(b.id) === String(boardId)) || null;
  return { boardId, board };
}