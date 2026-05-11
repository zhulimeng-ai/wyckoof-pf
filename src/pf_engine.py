import pandas as pd
import math
from typing import List, Dict, Literal, Optional, Tuple
from dataclasses import dataclass

@dataclass
class TRObject:
    """交易区间对象"""
    start_idx: int  # 起始列索引
    end_idx: int    # 结束列索引
    high: float     # 最高价
    low: float      # 最低价
    column_count: int  # 列数
    boxes_per_column: int  # 每列的格子数（用于计算宽高比）

class PFEngine:
    def __init__(self, box_size_type: Literal['point', 'percent'] = 'point', 
                 box_size_value: float = 1.0, reversal: int = 3):
        self.box_size_type = box_size_type
        self.box_size_value = box_size_value
        self.reversal = reversal

    def get_box_size(self, price: float) -> float:
        if self.box_size_type == 'percent':
            return price * (self.box_size_value / 100)
        return self.box_size_value

    def calculate_pf(self, data: pd.Series) -> List[Dict]:
        if len(data) < 1: return []

        columns = []
        # 初始化
        first_price = data.iloc[0]
        it = iter(data)
        next(it)
        
        current_type = None
        current_price = first_price # 當前列的最後一個箱子的價格
        current_boxes = []
        current_timestamps = [data.index[0]]
        
        # 尋找第一個趨勢
        box_size = self.get_box_size(first_price)
        for price in it:
            diff = price - first_price
            if abs(diff) >= box_size:
                current_type = 'X' if diff > 0 else 'O'
                num_boxes = int(abs(diff) / box_size)
                # 確定起始箱子位置（對齊 Box Size）
                base_price = first_price
                for i in range(num_boxes):
                    new_box = base_price + (box_size if current_type == 'X' else -box_size)
                    current_boxes.append(new_box)
                    base_price = new_box
                current_price = current_boxes[-1]
                break
        
        if current_type is None: return []

        # 開始主循環
        for price in it:
            # 在同一列中保持 Box Size 穩定，避免百分比漂移
            # 這裡使用當前列已確定的最後一個格子價格作為基準
            box_size = self.get_box_size(current_price)
            
            if current_type == 'X':
                # 1. 繼續上漲
                if price >= current_price + box_size:
                    num_new_boxes = int((price - current_price) / box_size)
                    for _ in range(num_new_boxes):
                        current_price += box_size
                        current_boxes.append(current_price)
                    current_timestamps.append(data.index[data.get_loc(price) if hasattr(data, 'get_loc') else 0])
                
                # 2. 檢查反轉 (下跌)
                elif price <= current_price - (self.reversal * box_size):
                    # 結算當前列
                    columns.append(self._create_col(current_type, current_boxes, current_timestamps))
                    # 切換到 O
                    current_type = 'O'
                    # 反轉後的第一格必定是前一列最高點下降一格
                    new_box_start = current_price - box_size
                    current_boxes = [new_box_start]
                    current_price = new_box_start
                    # 填充剩餘下跌部分
                    num_extra = int((current_price - price) / box_size)
                    for _ in range(num_extra):
                        current_price -= box_size
                        current_boxes.append(current_price)
                    current_timestamps = [data.index[data.get_loc(price) if hasattr(data, 'get_loc') else 0]]

            elif current_type == 'O':
                # 1. 繼續下跌
                if price <= current_price - box_size:
                    num_new_boxes = int((current_price - price) / box_size)
                    for _ in range(num_new_boxes):
                        current_price -= box_size
                        current_boxes.append(current_price)
                    current_timestamps.append(data.index[data.get_loc(price) if hasattr(data, 'get_loc') else 0])
                
                # 2. 檢查反轉 (上漲)
                elif price >= current_price + (self.reversal * box_size):
                    columns.append(self._create_col(current_type, current_boxes, current_timestamps))
                    current_type = 'X'
                    new_box_start = current_price + box_size
                    current_boxes = [new_box_start]
                    current_price = new_box_start
                    num_extra = int((price - current_price) / box_size)
                    for _ in range(num_extra):
                        current_price += box_size
                        current_boxes.append(current_price)
                    current_timestamps = [data.index[data.get_loc(price) if hasattr(data, 'get_loc') else 0]]

        # 最後一列處理
        if current_boxes:
            columns.append(self._create_col(current_type, current_boxes, current_timestamps))
            
        return columns

    def _create_col(self, c_type, boxes, times):
        return {
            'column_type': c_type,
            'start_price': boxes[0],
            'end_price': boxes[-1],
            'boxes_count': len(boxes),
            'boxes': boxes,
            'original_timestamps': [times[0], times[-1]]
        }

    def calculate_pf_dataframe(self, data: pd.Series) -> pd.DataFrame:
        columns = self.calculate_pf(data)
        df_list = []
        for i, col in enumerate(columns):
            for p in col['boxes']:
                df_list.append({
                    'column': i,
                    'type': col['column_type'],
                    'price': p,
                    'time': col['original_timestamps'][0]
                })
        return pd.DataFrame(df_list)
    
    def _get_column_price_range(self, pf_data: pd.DataFrame, col_idx: int) -> Tuple[float, float]:
        """获取指定列的价格范围
        
        参数:
            pf_data: 点数图数据
            col_idx: 列索引
            
        返回:
            (最低价, 最高价)
        """
        col_data = pf_data[pf_data['column'] == col_idx]
        if col_data.empty:
            return (float('inf'), float('-inf'))
        return (col_data['price'].min(), col_data['price'].max())
    
    def _calculate_overlap_ratio(self, range1: Tuple[float, float], range2: Tuple[float, float]) -> float:
        """计算两个价格范围的重叠比例
        
        参数:
            range1: (low1, high1)
            range2: (low2, high2)
            
        返回:
            重叠比例 (0-1)
        """
        low1, high1 = range1
        low2, high2 = range2
        
        # 计算重叠区间
        overlap_low = max(low1, low2)
        overlap_high = min(high1, high2)
        
        if overlap_high <= overlap_low:
            return 0.0
        
        overlap_length = overlap_high - overlap_low
        
        # 计算每个范围的高度
        height1 = high1 - low1
        height2 = high2 - low2
        
        if height1 == 0 or height2 == 0:
            return 0.0
        
        # 返回重叠部分占较小范围的比例
        return overlap_length / min(height1, height2)
    
    def _check_tr_initialization(self, pf_data: pd.DataFrame, start_col: int) -> bool:
        """检查TR初始化条件（LHS-Mid-RHS规则）
        
        参数:
            pf_data: 点数图数据
            start_col: 起始列索引
            
        返回:
            是否满足初始化条件
        """
        # 需要至少5列
        if start_col + 4 >= pf_data['column'].max():
            return False
        
        # 获取5列的价格范围
        ranges = []
        for i in range(5):
            ranges.append(self._get_column_price_range(pf_data, start_col + i))
        
        # 检查RHS条件：第4,5列与第3列的重叠率>20%
        rhs_condition = True
        for i in range(3, 5):
            overlap = self._calculate_overlap_ratio(ranges[i], ranges[2])
            if overlap <= 0.2:
                rhs_condition = False
                break
        
        # 检查RHS条件：第4列与第3列的重叠率>50%
        rhs_condition_2 = self._calculate_overlap_ratio(ranges[3], ranges[2]) > 0.5
        
        # 检查LHS条件：第4,5列与第1列的重叠率<20%
        lhs_condition = True
        for i in range(3, 5):
            overlap = self._calculate_overlap_ratio(ranges[i], ranges[0])
            if overlap >= 0.2:
                lhs_condition = False
                break
        
        return rhs_condition and rhs_condition_2 and lhs_condition
    
    def _check_tr_expansion(self, pf_data: pd.DataFrame, new_col_idx: int, tr_start: int, tr_end: int) -> bool:
        """检查TR扩展条件
        
        参数:
            pf_data: 点数图数据
            new_col_idx: 新列索引
            tr_start: TR起始列
            tr_end: TR结束列
            
        返回:
            是否满足扩展条件
        """
        # 获取新列的价格范围
        new_range = self._get_column_price_range(pf_data, new_col_idx)
        
        # 获取RHS三列（最后三列）的价格范围
        rhs_ranges = []
        for i in range(max(tr_start, tr_end - 2), tr_end + 1):
            rhs_ranges.append(self._get_column_price_range(pf_data, i))
        
        # 计算新列与RHS三列的重叠率
        rhs_overlap_ok = False
        for rhs_range in rhs_ranges:
            overlap = self._calculate_overlap_ratio(new_range, rhs_range)
            if overlap >= 0.5:
                rhs_overlap_ok = True
                break
        
        if not rhs_overlap_ok:
            return False
        
        # 获取LHS三列（前三列）的价格范围
        lhs_ranges = []
        for i in range(tr_start, min(tr_start + 3, tr_end + 1)):
            lhs_ranges.append(self._get_column_price_range(pf_data, i))
        
        # 计算新列与LHS三列的重叠率
        lhs_overlap_ok = False
        for lhs_range in lhs_ranges:
            overlap = self._calculate_overlap_ratio(new_range, lhs_range)
            if overlap >= 0.5:
                lhs_overlap_ok = True
                break
        
        return lhs_overlap_ok
    
    def _check_aspect_ratio(self, tr_high: float, tr_low: float, column_count: int) -> bool:
        """检查宽高比
        
        参数:
            tr_high: TR最高价
            tr_low: TR最低价
            column_count: TR列数
            
        返回:
            是否满足宽高比要求（<=1.5）
        """
        if column_count == 0:
            return False
        
        # 计算宽高比
        aspect_ratio = (tr_high - tr_low) / (column_count * self.box_size_value)
        
        # 如果比例大于1.5，则剔除
        return aspect_ratio <= 1.5
    
    def find_best_tr(self, pf_data: pd.DataFrame, start_col_idx: int, end_col_idx: int) -> Optional[TRObject]:
        """寻找最佳交易区间
        
        参数:
            pf_data: 点数图数据
            start_col_idx: 用户框选的起始列索引
            end_col_idx: 用户框选的结束列索引
            
        返回:
            最佳TR对象，如果没有找到则返回None
        """
        if pf_data is None or pf_data.empty:
            return None
        
        max_col = pf_data['column'].max()
        
        # 确保索引在有效范围内
        start_col_idx = max(0, start_col_idx)
        end_col_idx = min(max_col, end_col_idx)
        
        best_tr = None
        
        # 遍历所有可能的起始列
        for start_col in range(start_col_idx, end_col_idx - 3):
            # 检查初始化条件
            if not self._check_tr_initialization(pf_data, start_col):
                continue
            
            # 初始化TR
            tr_end = start_col + 4
            tr_ranges = [self._get_column_price_range(pf_data, i) for i in range(start_col, tr_end + 1)]
            tr_high = max(r[1] for r in tr_ranges)
            tr_low = min(r[0] for r in tr_ranges)
            
            # 尝试扩展TR
            for new_col in range(tr_end + 1, end_col_idx + 1):
                if self._check_tr_expansion(pf_data, new_col, start_col, tr_end):
                    tr_end = new_col
                    # 更新TR的高低范围
                    new_range = self._get_column_price_range(pf_data, new_col)
                    tr_high = max(tr_high, new_range[1])
                    tr_low = min(tr_low, new_range[0])
                else:
                    break
            
            # 检查宽高比
            column_count = tr_end - start_col + 1
            if not self._check_aspect_ratio(tr_high, tr_low, column_count):
                continue
            
            # 计算每列的平均格子数
            total_boxes = 0
            for col_idx in range(start_col, tr_end + 1):
                col_data = pf_data[pf_data['column'] == col_idx]
                total_boxes += len(col_data)
            boxes_per_column = total_boxes / column_count if column_count > 0 else 0
            
            # 创建TR对象
            tr = TRObject(
                start_idx=start_col,
                end_idx=tr_end,
                high=tr_high,
                low=tr_low,
                column_count=column_count,
                boxes_per_column=boxes_per_column
            )
            
            # 选择最长的TR
            if best_tr is None or tr.column_count > best_tr.column_count:
                best_tr = tr
        
        return best_tr
    
    def calculate_target_price(self, tr: TRObject, direction: Literal['bullish', 'bearish']) -> float:
        """计算目标价格
        
        参数:
            tr: 交易区间对象
            direction: 方向 ('bullish' 看涨, 'bearish' 看跌)
            
        返回:
            目标价格
        """
        if direction == 'bullish':
            # 看涨目标: TR_Low + (列数 × BoxSize × Reversal)
            return tr.low + (tr.column_count * self.box_size_value * self.reversal)
        else:
            # 看跌目标: TR_High - (列数 × BoxSize × Reversal)
            return tr.high - (tr.column_count * self.box_size_value * self.reversal)