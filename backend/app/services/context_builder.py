
# Not required 
# from sqlalchemy.orm import Session

# from app.models.board import Board
# from app.models.column import BoardColumn
# from app.models.task import Task
# from app.models.chat import Chat


# def build_context(
#     db: Session,
#     board_id: int,
#     limit: int = 20
# ) -> str:

#     board = db.query(Board).filter(
#         Board.id == board_id
#     ).first()

#     if not board:
#         return "Board not found."

#     columns = db.query(BoardColumn).filter(
#         BoardColumn.board_id == board_id
#     ).all()

#     tasks = (
#         db.query(Task)
#         .join(BoardColumn)
#         .filter(BoardColumn.board_id == board_id)
#         .all()
#     )

#     chats = (
#         db.query(Chat)
#         .filter(Chat.board_id == board_id)
#         .order_by(Chat.created_at.desc())
#         .limit(limit)
#         .all()
#     )

#     chats.reverse()

#     context = f"""
# Board Name:
# {board.name}

# Board Description:
# {board.description}

# Columns:
# """

#     for column in columns:
#         context += f"- {column.name}\n"

#     context += "\nTasks:\n"

#     for task in tasks:
#         context += f"""
# Title: {task.title}
# Description: {task.description}
# Priority: {task.priority}

# """

#     context += "\nPrevious Conversation:\n"

#     for chat in chats:
#         context += f"{chat.role}: {chat.message}\n"

#     return context

