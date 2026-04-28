#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
棋类对战平台 (Board Game Platform)
====================================
面向对象分析与设计课程大作业

实现五子棋和围棋的对战功能，支持玩家-玩家的双人对战。

设计模式:
    - Singleton(单例):    GamePlatform 游戏平台唯一实例
    - Strategy(策略):     RuleEngine 及其子类实现不同规则
    - Factory(工厂):      GameFactory 创建不同类型的游戏
    - Builder(建造者):    ConsoleViewBuilder 构建控制台界面
    - Template Method(模板方法): Game 定义游戏流程骨架
    - Memento(备忘录):    GameState 保存/恢复游戏状态

作者: liugangjian
日期: 2026-04
"""

import json
import os
import copy
from abc import ABC, abstractmethod

# ============================================================
# 常量定义
# ============================================================

BLACK = 1  # 黑子
WHITE = 2  # 白子
EMPTY = 0  # 空位

COLOR_SYMBOL = {
    BLACK: "●",  # 黑子显示符号
    WHITE: "○",  # 白子显示符号
    EMPTY: "+",  # 空位显示符号
}

COLOR_NAME = {
    BLACK: "黑方",
    WHITE: "白方",
}

MIN_BOARD_SIZE = 8
MAX_BOARD_SIZE = 19

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")


# ============================================================
# 辅助函数
# ============================================================

def color_to_str(color):
    """将颜色常量转为可读字符串"""
    return COLOR_NAME.get(color, "未知")


def pos_to_label(row, col, size):
    """
    将棋盘坐标 (row, col) 转为显示标签, 如 'D4'
    列用字母表示 (A-T, 跳过 I), 行用数字表示
    """
    # 列标: 跳过字母 I
    col_labels = []
    for i in range(26):
        ch = chr(ord('A') + i)
        if ch == 'I':
            continue
        col_labels.append(ch)
        if len(col_labels) >= size:
            break
    return col_labels[col] + str(row + 1)


def label_to_pos(label, size):
    """
    将显示标签 (如 'D4') 转为棋盘坐标 (row, col)
    返回 (row, col) 或 None 表示无效
    """
    if not label or len(label) < 2:
        return None
    label = label.strip().upper()
    # 解析列字母
    col_char = label[0]
    col_labels = []
    for i in range(26):
        ch = chr(ord('A') + i)
        if ch == 'I':
            continue
        col_labels.append(ch)
        if len(col_labels) >= size:
            break
    if col_char not in col_labels:
        return None
    col = col_labels.index(col_char)
    # 解析行数字
    try:
        row_num = int(label[1:])
    except ValueError:
        return None
    row = row_num - 1
    if row < 0 or row >= size or col < 0 or col >= size:
        return None
    return (row, col)


# ============================================================
# Move - 落子记录
# ============================================================

class Move:
    """
    落子记录类
    记录一次落子的完整信息，用于悔棋和历史记录。
    """

    def __init__(self, color, row, col, is_pass=False):
        """
        初始化落子记录

        Args:
            color: 落子方颜色 (BLACK/WHITE)
            row:   行号 (0-based), pass 时为 -1
            col:   列号 (0-based), pass 时为 -1
            is_pass: 是否为虚着 (pass)
        """
        self.color = color
        self.row = row
        self.col = col
        self.is_pass = is_pass
        # 记录因本次落子而被提走的子 (用于悔棋恢复)
        self.captured = []  # [(row, col, color), ...]

    def __repr__(self):
        if self.is_pass:
            return f"Move({color_to_str(self.color)}, PASS)"
        return f"Move({color_to_str(self.color)}, ({self.row},{self.col}))"

    def to_dict(self):
        """序列化为字典"""
        return {
            "color": self.color,
            "row": self.row,
            "col": self.col,
            "is_pass": self.is_pass,
            "captured": self.captured,
        }

    @classmethod
    def from_dict(cls, data):
        """从字典反序列化"""
        move = cls(data["color"], data["row"], data["col"], data["is_pass"])
        move.captured = [tuple(c) for c in data.get("captured", [])]
        return move


# ============================================================
# Player - 玩家
# ============================================================

class Player:
    """
    玩家类
    封装玩家信息。
    """

    def __init__(self, color, name=None):
        self.color = color
        self.name = name or color_to_str(color)

    def __repr__(self):
        return f"Player({self.name}, {COLOR_SYMBOL[self.color]})"


# ============================================================
# Board - 棋盘状态管理
# ============================================================

class Board:
    """
    棋盘类
    管理棋盘的状态，包括落子、提子、查询等操作。
    """

    def __init__(self, size):
        """
        初始化棋盘

        Args:
            size: 棋盘大小 (8-19)
        """
        if size < MIN_BOARD_SIZE or size > MAX_BOARD_SIZE:
            raise ValueError(f"棋盘大小必须在 {MIN_BOARD_SIZE}-{MAX_BOARD_SIZE} 之间")
        self.size = size
        # 二维数组表示棋盘状态: 0=空, 1=黑, 2=白
        self.grid = [[EMPTY] * size for _ in range(size)]

    def copy_grid(self):
        """返回棋盘的深拷贝"""
        return [row[:] for row in self.grid]

    def is_valid_pos(self, row, col):
        """检查坐标是否在棋盘范围内"""
        return 0 <= row < self.size and 0 <= col < self.size

    def get(self, row, col):
        """获取指定位置的状态"""
        return self.grid[row][col]

    def set(self, row, col, color):
        """在指定位置放置棋子"""
        self.grid[row][col] = color

    def remove(self, row, col):
        """移除指定位置的棋子 (提子)"""
        self.grid[row][col] = EMPTY

    def is_empty(self, row, col):
        """检查指定位置是否为空"""
        return self.grid[row][col] == EMPTY

    def count_stones(self, color):
        """统计指定颜色棋子数量"""
        count = 0
        for row in self.grid:
            count += row.count(color)
        return count

    def is_full(self):
        """检查棋盘是否已满"""
        for row in self.grid:
            if EMPTY in row:
                return False
        return True

    def to_dict(self):
        """序列化为字典"""
        return {"size": self.size, "grid": self.grid}

    @classmethod
    def from_dict(cls, data):
        """从字典反序列化"""
        board = cls(data["size"])
        board.grid = data["grid"]
        return board

    def grid_to_string(self):
        """将棋盘转为字符串, 用于比较棋盘状态 (Ko判定)"""
        rows = []
        for row in self.grid:
            rows.append("".join(str(c) for c in row))
        return "|".join(rows)

    def count_territory(self):
        """
        计算双方领地 (中国规则 - 数目法)
        返回 (black_territory, white_territory)
        领地 = 棋子数 + 只被一方围住的空点数
        """
        visited = [[False] * self.size for _ in range(self.size)]
        black_territory = 0
        white_territory = 0

        for r in range(self.size):
            for c in range(self.size):
                if visited[r][c]:
                    continue
                if self.grid[r][c] == BLACK:
                    black_territory += 1
                    visited[r][c] = True
                elif self.grid[r][c] == WHITE:
                    white_territory += 1
                    visited[r][c] = True
                else:
                    # 空点: BFS 找连通的空区域, 判断被谁包围
                    territory_owner = self._find_territory_owner(r, c, visited)
                    if territory_owner == BLACK:
                        black_territory += 1  # 整个连通区在调用中已累计
                    elif territory_owner == WHITE:
                        white_territory += 1
                    # territory_owner == None 表示中立区域, 不计入

        return black_territory, white_territory

    def _find_territory_owner(self, start_r, start_c, visited):
        """
        BFS 找到与 (start_r, start_c) 连通的空区域,
        判断该区域被哪一方包围。
        返回: BLACK / WHITE / None(中立或双方都相邻)
        整个连通区域的 visited 都会被标记。
        同时计算连通空点数。
        """
        queue = [(start_r, start_c)]
        visited[start_r][start_c] = True
        empty_count = 0
        adjacent_colors = set()
        region_cells = [(start_r, start_c)]

        while queue:
            r, c = queue.pop(0)
            empty_count += 1
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if not self.is_valid_pos(nr, nc):
                    continue
                if self.grid[nr][nc] != EMPTY:
                    adjacent_colors.add(self.grid[nr][nc])
                elif not visited[nr][nc]:
                    visited[nr][nc] = True
                    queue.append((nr, nc))
                    region_cells.append((nr, nc))

        # 判断领地归属
        if adjacent_colors == {BLACK}:
            return BLACK
        elif adjacent_colors == {WHITE}:
            return WHITE
        else:
            # 中立区域: 被双方包围或无子相邻
            return None


# ============================================================
# RuleEngine (Strategy 策略模式) - 规则引擎抽象基类
# ============================================================

class RuleEngine(ABC):
    """
    规则引擎抽象基类 (Strategy 策略模式)

    策略模式: 将不同游戏的规则封装为独立的策略类,
    使得游戏可以使用不同的规则引擎而不需要修改游戏逻辑。
    """

    @abstractmethod
    def validate_move(self, board: 'Board', move: 'Move', history: list) -> tuple:
        """验证落子是否合法, 返回 (bool, str)"""
        ...

    @abstractmethod
    def check_win(self, board: 'Board', last_move: 'Move') -> int:
        """检查获胜方颜色 (BLACK/WHITE), 0=未结束"""
        ...

    @abstractmethod
    def check_draw(self, board: 'Board') -> bool:
        """检查是否平局"""
        ...

    @abstractmethod
    def process_captures(self, board: 'Board', move: 'Move') -> list:
        """处理提子, 返回被提掉的子列表 [(row, col, color)]"""
        ...

    @abstractmethod
    def can_pass(self) -> bool:
        """该规则是否允许虚着 (pass)"""
        ...

    @abstractmethod
    def is_game_over_condition(self, consecutive_passes: int) -> bool:
        """根据连续 pass 次数判断游戏是否结束"""
        ...


# ============================================================
# GomokuRules - 五子棋规则
# ============================================================

class GomokuRules(RuleEngine):
    """
    五子棋规则 (Strategy 策略模式 - 具体策略)

    规则说明:
    - 黑白双方交替落子
    - 先连成五子 (横/竖/斜) 者胜
    - 棋盘满则平局
    - 不允许虚着 (pass)
    """

    def validate_move(self, board, move, history):
        """验证五子棋落子合法性"""
        if move.is_pass:
            return False, "五子棋不支持虚着 (pass)"
        if not board.is_valid_pos(move.row, move.col):
            return False, f"位置 ({move.row},{move.col}) 超出棋盘范围"
        if not board.is_empty(move.row, move.col):
            return False, f"位置 {pos_to_label(move.row, move.col, board.size)} 已有棋子"
        return True, "合法"

    def check_win(self, board, last_move):
        """
        检查五子连珠
        四个方向: 水平、垂直、左上-右下对角线、右上-左下对角线
        """
        if last_move is None or last_move.is_pass:
            return 0
        color = last_move.color
        r, c = last_move.row, last_move.col
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1  # 包括自身
            # 正方向
            for i in range(1, 5):
                nr, nc = r + dr * i, c + dc * i
                if board.is_valid_pos(nr, nc) and board.get(nr, nc) == color:
                    count += 1
                else:
                    break
            # 反方向
            for i in range(1, 5):
                nr, nc = r - dr * i, c - dc * i
                if board.is_valid_pos(nr, nc) and board.get(nr, nc) == color:
                    count += 1
                else:
                    break
            if count >= 5:
                return color
        return 0

    def check_draw(self, board):
        """棋盘满则平局"""
        return board.is_full()

    def process_captures(self, board, move):
        """五子棋没有提子"""
        return []

    def can_pass(self):
        """五子棋不允许虚着"""
        return False

    def is_game_over_condition(self, consecutive_passes):
        """五子棋不会因 pass 结束"""
        return False


# ============================================================
# GoRules - 围棋规则
# ============================================================

class GoRules(RuleEngine):
    """
    围棋规则 (Strategy 策略模式 - 具体策略)

    规则说明:
    - 黑白双方交替落子, 黑先
    - 支持提子: 移除无气的棋子
    - 禁止自杀: 不能下在使自己无气且不提对方子的位置
    - 劫 (Ko): 不能重现上一步之前的棋盘状态 (简单劫)
    - 允许虚着 (pass): 双方连续 pass 则终局
    - 中国规则数目: 领地 = 棋子 + 围住的空点, 白方贴 7.5 目
    """

    KOMI = 7.5  # 贴目 (中国规则)

    def validate_move(self, board, move, history):
        """验证围棋落子合法性"""
        if move.is_pass:
            return True, "合法 (虚着)"

        if not board.is_valid_pos(move.row, move.col):
            return False, f"位置 ({move.row},{move.col}) 超出棋盘范围"

        if not board.is_empty(move.row, move.col):
            return False, f"位置 {pos_to_label(move.row, move.col, board.size)} 已有棋子"

        # 临时放置棋子, 检查自杀和劫
        test_board = Board(board.size)
        test_board.grid = board.copy_grid()
        test_board.set(move.row, move.col, move.color)

        # 先处理提子 (对方无气的子)
        opponent = WHITE if move.color == BLACK else BLACK
        captured = self._capture_stones(test_board, move.row, move.col, opponent)

        # 检查自杀: 落子后自身气为0且未提对方子
        if not captured:
            own_group = self._find_group(test_board, move.row, move.col)
            own_liberties = self._count_liberties(test_board, own_group)
            if own_liberties == 0:
                return False, "禁止自杀: 落子后自身无气且未提对方子"

        # 检查劫 (Ko): 不能重现上一步之前的棋盘状态
        if len(history) >= 1:
            # 保存提子后的棋盘状态用于比较
            prev_board_str = None
            # 查找上一步之前的棋盘字符串
            if len(history) >= 1:
                # 需要比较的是落子+提子后的棋盘与上一步之前的状态
                # history 中每个 move 都有 captured 信息
                # 简单做法: 回退一步得到之前棋盘状态
                prev_board = Board(board.size)
                prev_board.grid = board.copy_grid()
                # 当前 board 是落子前的状态, 即上一步完成后的状态
                # 我们需要检查: 新落子+提子后的状态 != 上上一步完成后的状态
                # 即 history[-1] 之前的状态
                pass

            # 简化 Ko 检测: 比较落子+提子后的棋盘与落子前的棋盘
            # 真正的 Ko: 不能回到上上步的棋盘状态
            if len(history) >= 2:
                # 回退两步得到上上步棋盘
                two_moves_ago_board = self._reconstruct_board(board, history, steps_back=2)
                if two_moves_ago_board is not None:
                    current_after = test_board.grid_to_string()
                    two_ago_str = two_moves_ago_board.grid_to_string()
                    if current_after == two_ago_str:
                        return False, "违反劫规则 (Ko): 不能重现之前的棋盘状态"

        return True, "合法"

    def _reconstruct_board(self, current_board, history, steps_back):
        """
        从当前棋盘回退指定步数, 重建棋盘状态
        用于 Ko 检测
        """
        if len(history) < steps_back:
            return None

        result = Board(current_board.size)
        result.grid = current_board.copy_grid()

        for i in range(steps_back):
            move = history[-(i + 1)]
            if not move.is_pass:
                # 撤销提子: 恢复被提走的子
                for cr, cc, cc_color in move.captured:
                    result.set(cr, cc, cc_color)
                # 撤销落子: 移除落下的子
                result.remove(move.row, move.col)

        return result

    def check_win(self, board, last_move):
        """
        围棋不通过连子判定胜负
        通过数目法在终局时计算
        返回 0 (未通过此方法判定胜负)
        """
        return 0

    def check_draw(self, board):
        """围棋的平局在终局数目时判定"""
        return False

    def process_captures(self, board, move):
        """
        处理围棋提子
        返回被提掉的子列表 [(row, col, color), ...]
        """
        if move.is_pass:
            return []

        opponent = WHITE if move.color == BLACK else BLACK
        captured = self._capture_stones(board, move.row, move.col, opponent)
        return captured

    def _capture_stones(self, board, row, col, opponent_color):
        """
        检查并提取落子位置相邻的对方无气棋子
        """
        captured = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if not board.is_valid_pos(nr, nc):
                continue
            if board.get(nr, nc) == opponent_color:
                group = self._find_group(board, nr, nc)
                liberties = self._count_liberties(board, group)
                if liberties == 0:
                    for gr, gc in group:
                        board.remove(gr, gc)
                        captured.append((gr, gc, opponent_color))
        return captured

    def _find_group(self, board, row, col):
        """
        BFS 找到与 (row, col) 连通的同色棋子组
        返回 [(r, c), ...]
        """
        color = board.get(row, col)
        if color == EMPTY:
            return []

        visited = set()
        queue = [(row, col)]
        visited.add((row, col))
        group = [(row, col)]

        while queue:
            r, c = queue.pop(0)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) in visited:
                    continue
                if board.is_valid_pos(nr, nc) and board.get(nr, nc) == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
                    group.append((nr, nc))

        return group

    def _count_liberties(self, board, group):
        """
        计算一个棋子组的气数
        气 = 与棋子组相邻的空点数
        """
        liberties = set()
        for r, c in group:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if board.is_valid_pos(nr, nc) and board.get(nr, nc) == EMPTY:
                    liberties.add((nr, nc))
        return len(liberties)

    def can_pass(self):
        """围棋允许虚着"""
        return True

    def is_game_over_condition(self, consecutive_passes):
        """双方连续 pass 则终局"""
        return consecutive_passes >= 2

    def calculate_score(self, board):
        """
        中国规则数目法计算得分
        返回 (black_score, white_score)
        黑方得分 = 黑子数 + 只被黑方围住的空点数
        白方得分 = 白子数 + 只被白方围住的空点数 + 贴目
        """
        black_territory, white_territory = board.count_territory()
        white_score = white_territory + self.KOMI
        return black_territory, white_score


# ============================================================
# GameState (Memento 备忘录模式) - 游戏状态快照
# ============================================================

class GameState:
    """
    游戏状态备忘录 (Memento 备忘录模式)

    备忘录模式: 在不破坏封装的前提下, 捕获游戏的内部状态,
    以便之后可以将游戏恢复到该状态。
    用于保存/加载游戏功能。
    """

    def __init__(self, game_type, board_data, current_player,
                 move_history, consecutive_passes, game_over, winner):
        """
        初始化游戏状态快照

        Args:
            game_type:         游戏类型 ("gomoku"/"go")
            board_data:        棋盘数据 (dict)
            current_player:    当前落子方颜色
            move_history:      历史落子记录 (list of dict)
            consecutive_passes:连续 pass 次数
            game_over:         游戏是否结束
            winner:            获胜方颜色 (0 表示平局/未结束)
        """
        self.game_type = game_type
        self.board_data = board_data
        self.current_player = current_player
        self.move_history = move_history
        self.consecutive_passes = consecutive_passes
        self.game_over = game_over
        self.winner = winner

    def to_dict(self):
        """序列化为字典"""
        return {
            "game_type": self.game_type,
            "board": self.board_data,
            "current_player": self.current_player,
            "move_history": self.move_history,
            "consecutive_passes": self.consecutive_passes,
            "game_over": self.game_over,
            "winner": self.winner,
        }

    @classmethod
    def from_dict(cls, data):
        """从字典反序列化"""
        return cls(
            game_type=data["game_type"],
            board_data=data["board"],
            current_player=data["current_player"],
            move_history=data["move_history"],
            consecutive_passes=data.get("consecutive_passes", 0),
            game_over=data.get("game_over", False),
            winner=data.get("winner", 0),
        )


# ============================================================
# SaveManager - 存档管理器
# ============================================================

class SaveManager:
    """
    存档管理器
    负责将 GameState 保存到文件和从文件加载。
    使用 JSON 格式存储。
    """

    @staticmethod
    def ensure_save_dir():
        """确保存档目录存在"""
        os.makedirs(SAVE_DIR, exist_ok=True)

    @staticmethod
    def save(state, filename):
        """
        保存游戏状态到文件

        Args:
            state:    GameState 实例
            filename: 文件名 (不含路径)

        Raises:
            IOError: 保存失败时抛出
        """
        SaveManager.ensure_save_dir()
        filepath = os.path.join(SAVE_DIR, filename)
        if not filename.endswith(".json"):
            filepath += ".json"
        try:
            data = state.to_dict()
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return filepath
        except (IOError, OSError) as e:
            raise IOError(f"保存失败: {e}")

    @staticmethod
    def load(filename):
        """
        从文件加载游戏状态

        Args:
            filename: 文件名 (不含路径)

        Returns:
            GameState 实例

        Raises:
            IOError/FileNotFoundError: 加载失败时抛出
        """
        filepath = os.path.join(SAVE_DIR, filename)
        if not filename.endswith(".json"):
            filepath += ".json"
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"存档文件不存在: {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return GameState.from_dict(data)
        except json.JSONDecodeError as e:
            raise IOError(f"存档文件格式错误: {e}")
        except (IOError, OSError) as e:
            raise IOError(f"加载失败: {e}")

    @staticmethod
    def list_saves():
        """列出所有存档文件"""
        SaveManager.ensure_save_dir()
        saves = []
        for f in os.listdir(SAVE_DIR):
            if f.endswith(".json"):
                saves.append(f)
        return sorted(saves)


# ============================================================
# ConsoleView & Builder (Builder 建造者模式) - 控制台视图
# ============================================================

class ConsoleView:
    """
    控制台视图
    负责所有控制台输出, 实现前后端分离中的"前端"。
    """

    def __init__(self):
        self.show_help_tips = True  # 是否显示帮助提示
        self.components = {}  # Builder 构建的组件

    def show_welcome(self):
        """显示欢迎信息"""
        print("\n" + "=" * 60)
        print("          欢迎来到棋类对战平台")
        print("     Board Game Platform - Gomoku & Go")
        print("=" * 60)
        if self.show_help_tips:
            print("\n提示: 输入 'help' 查看所有可用命令\n")

    def show_board(self, board, current_player=None):
        """
        显示棋盘

        棋盘格式:
          A B C D E F G H ...
        8 + + + + + + + +
        7 + + + + + + + +
        ...
        1 + + + + + + + +
        """
        size = board.size

        # 生成列标签 (跳过 I)
        col_labels = []
        for i in range(26):
            ch = chr(ord('A') + i)
            if ch == 'I':
                continue
            col_labels.append(ch)
            if len(col_labels) >= size:
                break

        # 打印列标签
        header = "  " + " ".join(col_labels)
        print(header)

        # 打印棋盘 (从大到小的行号)
        for row in range(size - 1, -1, -1):
            row_str = f"{row + 1:>2}"
            for col in range(size):
                cell = board.get(row, col)
                symbol = COLOR_SYMBOL.get(cell, "+")
                row_str += " " + symbol
            print(row_str)

        # 显示当前落子方
        if current_player is not None:
            symbol = COLOR_SYMBOL.get(current_player, "?")
            name = color_to_str(current_player)
            print(f"\n  当前落子: {symbol} {name}")

    def show_message(self, msg):
        """显示普通消息"""
        print(f"  {msg}")

    def show_error(self, msg):
        """显示错误消息"""
        print(f"  ✗ 错误: {msg}")

    def show_success(self, msg):
        """显示成功消息"""
        print(f"  ✓ {msg}")

    def show_info(self, msg):
        """显示提示信息"""
        print(f"  ℹ {msg}")

    def show_separator(self):
        """显示分隔线"""
        print("  " + "-" * 50)

    def show_help(self):
        """显示帮助信息"""
        print("\n" + "=" * 50)
        print("  可用命令列表")
        print("=" * 50)
        print("""
  new       - 开始新游戏 (选择棋类和棋盘大小)
  restart   - 重新开始当前游戏
  <坐标>    - 落子, 如 D4, H8, P15
  pass      - 虚着/跳过 (仅围棋)
  undo      - 悔棋 (撤销上一步)
  resign    - 投子认负
  save <名> - 保存游戏, 如 save mygame
  load <名> - 加载游戏, 如 load mygame
  list      - 列出所有存档
  help      - 显示此帮助
  tips      - 开关帮助提示
  quit      - 退出平台
""")
        print("=" * 50)

    def show_game_over(self, winner, reason=""):
        """显示游戏结束信息"""
        print("\n" + "=" * 50)
        if winner == 0:
            print("  游戏结束: 平局!")
        else:
            symbol = COLOR_SYMBOL.get(winner, "?")
            name = color_to_str(winner)
            print(f"  游戏结束: {symbol} {name} 获胜!")
        if reason:
            print(f"  原因: {reason}")
        print("=" * 50 + "\n")

    def show_go_score(self, black_score, white_score, komi):
        """显示围棋得分"""
        print(f"\n  ┌─────────────────────────────┐")
        print(f"  │  围棋计分 (中国规则)         │")
        print(f"  │                             │")
        print(f"  │  ● 黑方: {black_score:>6.1f} 目          │")
        print(f"  │  ○ 白方: {white_score:>6.1f} 目 (含贴{komi}目) │")
        print(f"  │                             │")
        diff = abs(black_score - white_score)
        if black_score > white_score:
            print(f"  │  ● 黑方胜 {diff:.1f} 目            │")
        elif white_score > black_score:
            print(f"  │  ○ 白方胜 {diff:.1f} 目            │")
        else:
            print(f"  │  平局                       │")
        print(f"  └─────────────────────────────┘\n")

    def show_move_history(self, moves, size):
        """显示落子历史"""
        print("\n  落子历史:")
        for i, move in enumerate(moves):
            if move.is_pass:
                print(f"    {i+1}. {color_to_str(move.color)}: PASS")
            else:
                label = pos_to_label(move.row, move.col, size)
                cap_info = ""
                if move.captured:
                    cap_info = f" (提{len(move.captured)}子)"
                print(f"    {i+1}. {color_to_str(move.color)}: {label}{cap_info}")
        print()


class ConsoleViewBuilder:
    """
    控制台视图建造者 (Builder 建造者模式)

    建造者模式: 将复杂对象的构建过程与其表示分离,
    使得同样的构建过程可以创建不同的表示。
    先设计后建造: 先配置各个组件, 再构建最终的视图对象。
    """

    def __init__(self):
        self._view = ConsoleView()
        self._built = False

    def set_help_tips(self, enabled):
        """设置是否显示帮助提示"""
        self._view.show_help_tips = enabled
        return self  # 链式调用

    def add_component(self, name, component):
        """
        添加视图组件
        Builder 模式: 逐步构建复杂对象的各个部分
        """
        self._view.components[name] = component
        return self

    def add_welcome_banner(self, banner_text):
        """添加自定义欢迎横幅"""
        self._view.components["welcome_banner"] = banner_text
        return self

    def add_color_scheme(self, black_sym, white_sym, empty_sym):
        """添加自定义颜色方案"""
        self._view.components["color_scheme"] = {
            "black": black_sym,
            "white": white_sym,
            "empty": empty_sym,
        }
        return self

    def add_title(self, title):
        """添加标题"""
        self._view.components["title"] = title
        return self

    def add_status_bar(self, enabled=True):
        """添加状态栏"""
        self._view.components["status_bar"] = enabled
        return self

    def add_move_counter(self, enabled=True):
        """添加落子计数器"""
        self._view.components["move_counter"] = enabled
        return self

    def build(self):
        """
        构建并返回最终的 ConsoleView 实例
        Builder 模式的核心: 将构建过程与最终产品分离
        """
        self._built = True
        return self._view


# ============================================================
# Game (Template Method 模板方法模式) - 游戏抽象基类
# ============================================================

class Game(ABC):
    """
    游戏抽象基类 (Template Method 模板方法模式)

    模板方法模式: 定义算法的骨架 (游戏流程),
    将某些步骤延迟到子类中实现。
    子类可以在不改变算法结构的情况下, 重新定义某些步骤。

    游戏流程骨架:
    1. initialize() - 初始化游戏
    2. play() 循环:
       a. display()    - 显示当前状态
       b. get_input()  - 获取玩家输入
       c. process()    - 处理输入/落子
       d. check()      - 检查胜负
    3. end_game() - 结束游戏
    """

    def __init__(self, board_size, rule_engine, view, game_type):
        """
        初始化游戏

        Args:
            board_size:  棋盘大小
            rule_engine: 规则引擎 (Strategy)
            view:        控制台视图
            game_type:   游戏类型标识
        """
        if board_size < MIN_BOARD_SIZE or board_size > MAX_BOARD_SIZE:
            raise ValueError(f"棋盘大小必须在 {MIN_BOARD_SIZE}-{MAX_BOARD_SIZE} 之间")
        self.board_size = board_size
        self.board = Board(board_size)
        self.rules = rule_engine  # Strategy: 组合规则引擎
        self.view = view
        self.game_type = game_type
        self.players = [Player(BLACK, "黑方"), Player(WHITE, "白方")]
        self.move_history = []
        self.current_player_idx = 0
        self.game_over = False
        self.winner = 0  # 0=未结束/平局
        self.consecutive_passes = 0
        self.winner_reason = ""

    @property
    def current_player(self):
        """获取当前玩家"""
        return self.players[self.current_player_idx]

    @property
    def current_color(self):
        """获取当前玩家颜色"""
        return self.current_player.color

    def switch_player(self):
        """切换当前玩家"""
        self.current_player_idx = 1 - self.current_player_idx

    # === Template Method: 定义游戏流程骨架 ===

    def run(self):
        """
        模板方法: 定义游戏的主流程骨架
        子类可以重写其中的钩子方法来自定义行为
        """
        self.initialize()
        self.display()
        while not self.game_over:
            cmd = self.get_input()
            if cmd is None:
                continue
            self.process(cmd)
            if not self.game_over:
                self.display()

    def initialize(self):
        """初始化游戏 (可被子类重写)"""
        self.view.show_message(f"游戏开始: {self.game_type_name()}")
        self.view.show_message(f"棋盘大小: {self.board_size}×{self.board_size}")

    @abstractmethod
    def game_type_name(self) -> str:
        """返回游戏类型名称"""
        ...

    def display(self):
        """显示当前游戏状态"""
        self.view.show_separator()
        self.view.show_board(self.board, self.current_color)
        # 显示落子计数
        if self.view.components.get("move_counter", True):
            self.view.show_info(f"第 {len(self.move_history)+1} 手")

    def get_input(self):
        """获取玩家输入"""
        try:
            prompt = f"  {color_to_str(self.current_color)} 请落子 (输入坐标如 D4, 或命令): "
            cmd = input(prompt).strip()
            return cmd
        except EOFError:
            return "quit"
        except KeyboardInterrupt:
            print()
            return "quit"

    def process(self, cmd):
        """
        处理玩家输入
        将命令分发到对应的处理方法
        """
        cmd_lower = cmd.lower()

        if cmd_lower == "help":
            self.view.show_help()
        elif cmd_lower == "tips":
            self.view.show_help_tips = not self.view.show_help_tips
            state = "开启" if self.view.show_help_tips else "关闭"
            self.view.show_success(f"帮助提示已{state}")
        elif cmd_lower == "restart":
            self.restart()
        elif cmd_lower == "undo":
            self.undo()
        elif cmd_lower == "resign":
            self.resign()
        elif cmd_lower == "pass":
            self.do_pass()
        elif cmd_lower.startswith("save"):
            self.handle_save(cmd)
        elif cmd_lower.startswith("load"):
            self.handle_load(cmd)
        elif cmd_lower == "list":
            self.list_saves()
        elif cmd_lower == "history":
            self.show_history()
        elif cmd_lower == "quit":
            self.game_over = True
            self.view.show_message("游戏结束, 感谢游玩!")
        else:
            # 尝试解析为落子坐标
            self.try_place(cmd)

    # === 具体操作方法 ===

    def try_place(self, cmd):
        """尝试解析并执行落子"""
        pos = label_to_pos(cmd, self.board_size)
        if pos is None:
            self.view.show_error(f"无效的输入: '{cmd}'. 输入 'help' 查看命令列表")
            return

        row, col = pos
        move = Move(self.current_color, row, col)

        # 验证落子合法性
        valid, reason = self.rules.validate_move(self.board, move, self.move_history)
        if not valid:
            self.view.show_error(reason)
            return

        # 执行落子
        self.board.set(row, col, self.current_color)
        self.consecutive_passes = 0

        # 处理提子
        captured = self.rules.process_captures(self.board, move)
        move.captured = captured

        # 记录历史
        self.move_history.append(move)

        # 显示落子信息
        label = pos_to_label(row, col, self.board_size)
        self.view.show_success(
            f"{color_to_str(move.color)} 落子 {label}"
            + (f" (提{len(captured)}子)" if captured else "")
        )

        # 检查胜负
        winner = self.rules.check_win(self.board, move)
        if winner:
            self.game_over = True
            self.winner = winner
            self.view.show_game_over(winner, self.get_win_reason())
            return

        # 检查平局
        if self.rules.check_draw(self.board):
            self.game_over = True
            self.winner = 0
            self.view.show_game_over(0, "棋盘已满")
            return

        # 切换玩家
        self.switch_player()

    def do_pass(self):
        """执行虚着 (pass)"""
        if not self.rules.can_pass():
            self.view.show_error("当前游戏不支持虚着 (pass)")
            return

        move = Move(self.current_color, -1, -1, is_pass=True)
        self.move_history.append(move)
        self.consecutive_passes += 1
        self.view.show_success(f"{color_to_str(self.current_color)} 选择虚着 (PASS)")

        # 检查是否因连续 pass 终局
        if self.rules.is_game_over_condition(self.consecutive_passes):
            self.end_by_scoring()
            return

        self.switch_player()

    def undo(self):
        """悔棋: 撤销上一步"""
        if not self.move_history:
            self.view.show_error("没有可以悔的棋")
            return

        last_move = self.move_history.pop()

        if not last_move.is_pass:
            # 恢复落子: 移除该步棋子
            self.board.remove(last_move.row, last_move.col)

            # 恢复被提的子
            for cr, cc, cc_color in last_move.captured:
                self.board.set(cr, cc, cc_color)

        # 重置连续 pass 计数
        # 回退后需要重新计算
        self.consecutive_passes = 0
        for m in reversed(self.move_history):
            if m.is_pass:
                self.consecutive_passes += 1
            else:
                break

        # 切换回上一位玩家
        self.current_player_idx = 1 - self.current_player_idx

        self.view.show_success(
            f"悔棋成功: 撤销了 {color_to_str(last_move.color)} 的"
            + ("虚着" if last_move.is_pass else f"落子 {pos_to_label(last_move.row, last_move.col, self.board_size)}")
        )

    def resign(self):
        """投子认负"""
        loser = self.current_color
        winner = WHITE if loser == BLACK else BLACK
        self.game_over = True
        self.winner = winner
        self.winner_reason = f"{color_to_str(loser)} 投子认负"
        self.view.show_game_over(winner, self.winner_reason)

    def restart(self):
        """重新开始当前游戏"""
        self.board = Board(self.board_size)
        self.move_history = []
        self.current_player_idx = 0
        self.game_over = False
        self.winner = 0
        self.consecutive_passes = 0
        self.winner_reason = ""
        self.view.show_success("游戏已重新开始!")
        self.view.show_board(self.board, self.current_color)

    def handle_save(self, cmd):
        """处理保存命令"""
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            self.view.show_error("用法: save <存档名>, 如: save mygame")
            return
        filename = parts[1].strip()
        try:
            state = self._create_state()
            path = SaveManager.save(state, filename)
            self.view.show_success(f"游戏已保存到: {path}")
        except (IOError, OSError) as e:
            self.view.show_error(str(e))

    def handle_load(self, cmd):
        """处理加载命令"""
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            self.view.show_error("用法: load <存档名>, 如: load mygame")
            return
        filename = parts[1].strip()
        try:
            state = SaveManager.load(filename)
            self._restore_state(state)
            self.view.show_success(f"游戏已从存档加载!")
            self.view.show_board(self.board, self.current_color)
        except (FileNotFoundError, IOError) as e:
            self.view.show_error(str(e))

    def list_saves(self):
        """列出所有存档"""
        saves = SaveManager.list_saves()
        if not saves:
            self.view.show_info("暂无存档文件")
        else:
            self.view.show_message("存档列表:")
            for s in saves:
                self.view.show_message(f"  - {s}")

    def show_history(self):
        """显示落子历史"""
        if not self.move_history:
            self.view.show_info("暂无落子记录")
        else:
            self.view.show_move_history(self.move_history, self.board_size)

    # === 状态管理 (Memento) ===

    def _create_state(self):
        """创建当前游戏状态的备忘录 (Memento)"""
        return GameState(
            game_type=self.game_type,
            board_data=self.board.to_dict(),
            current_player=self.current_color,
            move_history=[m.to_dict() for m in self.move_history],
            consecutive_passes=self.consecutive_passes,
            game_over=self.game_over,
            winner=self.winner,
        )

    def _restore_state(self, state):
        """从备忘录恢复游戏状态 (Memento)"""
        self.board = Board.from_dict(state.board_data)
        self.move_history = [Move.from_dict(m) for m in state.move_history]
        self.consecutive_passes = state.consecutive_passes
        self.game_over = state.game_over
        self.winner = state.winner
        # 恢复当前玩家
        if state.current_player == BLACK:
            self.current_player_idx = 0
        else:
            self.current_player_idx = 1

    @abstractmethod
    def get_win_reason(self) -> str:
        """获取胜利原因描述"""
        ...

    @abstractmethod
    def end_by_scoring(self):
        """通过计分结束游戏 (围棋特有)"""
        ...


# ============================================================
# GomokuGame - 五子棋游戏
# ============================================================

class GomokuGame(Game):
    """
    五子棋游戏 (Template Method - 具体实现)

    五子棋特殊规则:
    - 先连成五子者胜
    - 棋盘满则平局
    - 不支持 pass
    """

    def __init__(self, board_size, view):
        """创建五子棋游戏, 使用五子棋规则引擎 (Strategy)"""
        rules = GomokuRules()
        super().__init__(board_size, rules, view, "gomoku")

    def game_type_name(self):
        return "五子棋 (Gomoku)"

    def get_win_reason(self):
        return "五子连珠"

    def end_by_scoring(self):
        """五子棋不支持计分结束"""
        self.view.show_error("五子棋不支持计分结束")


# ============================================================
# GoGame - 围棋游戏
# ============================================================

class GoGame(Game):
    """
    围棋游戏 (Template Method - 具体实现)

    围棋特殊规则:
    - 支持提子
    - 支持 pass
    - 双方连续 pass 终局
    - 中国规则数目法计分
    """

    def __init__(self, board_size, view):
        """创建围棋游戏, 使用围棋规则引擎 (Strategy)"""
        rules = GoRules()
        super().__init__(board_size, rules, view, "go")

    def game_type_name(self):
        return "围棋 (Go)"

    def get_win_reason(self):
        return "投子认负"

    def end_by_scoring(self):
        """
        通过数目法结束游戏
        中国规则: 领地 = 棋子 + 围住的空点
        白方贴 7.5 目
        """
        self.game_over = True
        black_score, white_score = self.rules.calculate_score(self.board)
        komi = GoRules.KOMI

        self.view.show_go_score(black_score, white_score, komi)

        if black_score > white_score:
            self.winner = BLACK
            diff = black_score - white_score
            self.winner_reason = f"黑方胜 {diff:.1f} 目"
        elif white_score > black_score:
            self.winner = WHITE
            diff = white_score - black_score
            self.winner_reason = f"白方胜 {diff:.1f} 目 (含贴{komi}目)"
        else:
            self.winner = 0
            self.winner_reason = "平局"

        self.view.show_game_over(self.winner, self.winner_reason)


# ============================================================
# GameFactory (Factory 工厂模式) - 游戏工厂
# ============================================================

class GameFactory:
    """
    游戏工厂 (Factory 工厂模式)

    工厂模式: 定义创建对象的接口, 让子类决定实例化哪个类。
    客户端通过工厂创建游戏, 不需要知道具体的游戏类。

    客户端统一使用 Game 接口, 多态地调用不同游戏的方法。
    """

    GAME_TYPES = {
        "gomoku": "五子棋",
        "go": "围棋",
    }

    @staticmethod
    def create_game(game_type, board_size, view):
        """
        根据游戏类型创建对应的游戏实例

        Args:
            game_type:  游戏类型 ("gomoku" / "go")
            board_size: 棋盘大小
            view:       控制台视图

        Returns:
            Game 子类实例

        Raises:
            ValueError: 不支持的游戏类型
        """
        if game_type == "gomoku":
            return GomokuGame(board_size, view)
        elif game_type == "go":
            return GoGame(board_size, view)
        else:
            raise ValueError(
                f"不支持的游戏类型: '{game_type}'. "
                f"支持的类型: {', '.join(GameFactory.GAME_TYPES.keys())}"
            )

    @staticmethod
    def list_types():
        """列出所有支持的游戏类型"""
        return GameFactory.GAME_TYPES.copy()

    @staticmethod
    def create_from_state(state, view):
        """
        从存档状态恢复游戏实例

        Args:
            state: GameState 备忘录
            view:  控制台视图

        Returns:
            恢复后的 Game 子类实例
        """
        game = GameFactory.create_game(state.game_type, state.board_data["size"], view)
        game._restore_state(state)
        return game


# ============================================================
# GamePlatform (Singleton 单例模式) - 游戏平台主控制器
# ============================================================

class GamePlatform:
    """
    游戏平台 (Singleton 单例模式)

    单例模式: 确保一个类只有一个实例, 并提供全局访问点。
    平台只有一个实例, 管理所有游戏的创建和运行。

    作为系统的主控制器, 协调各个组件:
    - 通过 GameFactory 创建游戏 (Factory)
    - 通过 ConsoleViewBuilder 构建视图 (Builder)
    - 通过 Game 运行游戏 (Template Method)
    """

    _instance = None  # 单例实例

    def __new__(cls):
        """单例模式: 确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化平台"""
        if self._initialized:
            return
        self._initialized = True
        self.current_game = None
        self.running = True

        # Builder 模式构建视图
        self.view = (
            ConsoleViewBuilder()
            .set_help_tips(True)
            .add_title("棋类对战平台")
            .add_color_scheme("●", "○", "+")
            .add_status_bar(True)
            .add_move_counter(True)
            .build()
        )

    def start(self):
        """启动平台主循环"""
        self.view.show_welcome()

        while self.running:
            try:
                self._main_menu()
            except (KeyboardInterrupt, EOFError):
                print()
                self.view.show_message("已退出平台, 感谢游玩!")
                self.running = False
            except Exception as e:
                self.view.show_error(f"发生错误: {e}")

    def _main_menu(self):
        """主菜单循环"""
        if self.current_game and not self.current_game.game_over:
            # 游戏进行中
            cmd = self.current_game.get_input()
            if cmd is not None:
                self.current_game.process(cmd)
            return

        # 没有游戏在进行, 显示主菜单
        print("\n" + "=" * 50)
        print("  主菜单")
        print("=" * 50)
        print("  1. 开始新游戏")
        print("  2. 加载存档")
        print("  3. 退出平台")
        print("=" * 50)

        choice = input("  请选择 (1-3): ").strip()

        if choice == "1":
            self._new_game()
        elif choice == "2":
            self._load_game_menu()
        elif choice == "3":
            self.view.show_message("感谢使用棋类对战平台, 再见!")
            self.running = False
        else:
            self.view.show_error("无效选择, 请输入 1-3")

    def _new_game(self):
        """创建新游戏"""
        # 选择游戏类型
        print("\n  选择游戏类型:")
        types = GameFactory.list_types()
        for i, (key, name) in enumerate(types.items(), 1):
            print(f"    {i}. {name}")

        choice = input("  请选择 (1-2): ").strip()
        if choice == "1":
            game_type = "gomoku"
        elif choice == "2":
            game_type = "go"
        else:
            self.view.show_error("无效选择")
            return

        # 选择棋盘大小
        if game_type == "gomoku":
            default_size = 15
            print(f"\n  五子棋标准棋盘为 15×15")
        else:
            default_size = 19
            print(f"\n  围棋标准棋盘为 19×19")

        size_input = input(
            f"  请输入棋盘大小 ({MIN_BOARD_SIZE}-{MAX_BOARD_SIZE}, 回车默认{default_size}): "
        ).strip()

        if size_input == "":
            board_size = default_size
        else:
            try:
                board_size = int(size_input)
                if board_size < MIN_BOARD_SIZE or board_size > MAX_BOARD_SIZE:
                    self.view.show_error(
                        f"棋盘大小必须在 {MIN_BOARD_SIZE}-{MAX_BOARD_SIZE} 之间"
                    )
                    return
            except ValueError:
                self.view.show_error("请输入有效的数字")
                return

        # 通过工厂创建游戏 (Factory Pattern + Polymorphism)
        try:
            self.current_game = GameFactory.create_game(
                game_type, board_size, self.view
            )
            # 运行游戏
            self.current_game.initialize()
            self.current_game.display()
        except ValueError as e:
            self.view.show_error(str(e))

    def _load_game_menu(self):
        """加载存档菜单"""
        saves = SaveManager.list_saves()
        if not saves:
            self.view.show_info("暂无存档文件")
            return

        print("\n  可用存档:")
        for i, s in enumerate(saves, 1):
            print(f"    {i}. {s}")

        filename = input("  请输入存档名 (或回车返回): ").strip()
        if not filename:
            return

        try:
            state = SaveManager.load(filename)
            self.current_game = GameFactory.create_from_state(state, self.view)
            self.view.show_success("游戏已加载!")
            self.view.show_board(self.current_game.board, self.current_game.current_color)
        except (FileNotFoundError, IOError) as e:
            self.view.show_error(str(e))

    @classmethod
    def reset_instance(cls):
        """重置单例 (仅用于测试)"""
        cls._instance = None


# ============================================================
# main - 程序入口
# ============================================================

def main():
    """
    程序入口

    演示棋类对战平台的完整功能:
    1. 使用 Singleton 获取平台实例
    2. 使用 Builder 构建视图
    3. 使用 Factory 创建游戏
    4. 使用 Strategy 切换规则
    5. 使用 Template Method 运行游戏流程
    6. 使用 Memento 保存/加载游戏
    """
    # Singleton: 获取平台唯一实例
    platform = GamePlatform()
    platform.start()


if __name__ == "__main__":
    main()
