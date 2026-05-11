import pyqtgraph as pg
from PyQt5.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
import numpy as np


class SquareViewBox(pg.ViewBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAspectLocked(True, 1.0)
    
    def updateAutoRange(self):
        super().updateAutoRange()
        self.setAspectLocked(True, 1.0)


class PFChartWidget(pg.GraphicsLayoutWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('w')
        
        self.plot_item = self.addPlot()
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.setLabel('left', 'Price')
        self.plot_item.setLabel('bottom', 'Column')
        
        self.custom_chart_item = None
        self.wyckoff_target_item = None  # 威科夫目标价预测组件
        self.box_size = 1.0
        self.box_size_type = 'point'
        self.min_price = None
        self.growth_rate = None
        self.pf_engine = None  # PFEngine实例
        self.pf_data = None  # 点数图数据
        
        self.plot_item.setMouseEnabled(x=True, y=True)
        self.plot_item.setMenuEnabled(False)
        
        self.proxy = pg.SignalProxy(self.plot_item.scene().sigMouseMoved, 
                                     rateLimit=60, slot=self.mouse_moved)
        
        # 连接缩放信号，实现动态轴刻度
        self.plot_item.vb.sigRangeChanged.connect(self.on_range_changed)
        
        # 鼠标拖拽相关变量
        self.drag_start = None
        self.drag_end = None
        self.is_dragging = False
        self.drag_rect_item = None  # 拖拽框选矩形
        self.mouse_pressed = False  # 鼠标是否按下
        self.hand_mode = False  # 手模式（用于拖拽窗口）
        self._update_pending = False  # 防抖标志，避免频繁更新轴刻度
        
        # 安装事件过滤器
        self.plot_item.scene().installEventFilter(self)
        # 安装事件过滤器到窗口，處理鼠標鍵盤
        self.installEventFilter(self)
    
    def set_aspect_ratio_locked(self, locked=True):
        self.plot_item.setAspectLocked(locked, 1.0)
    
    def clear_chart(self):
        if self.custom_chart_item:
            self.plot_item.removeItem(self.custom_chart_item)
            self.custom_chart_item = None
    
    def plot_pf_data(self, pf_data, box_size=1.0, box_size_type='point'):
        """绘制Point & Figure数据
        
        参数:
            pf_data: 包含column, type, price列的DataFrame
            box_size: box size数值
            box_size_type: 'point' 或 'percent'
        """
        self.clear_chart()
        self.box_size = box_size
        self.box_size_type = box_size_type
        
        if pf_data is None or pf_data.empty:
            return
        
        # 对于百分比类型，使用网格索引映射法
        if box_size_type == 'percent':
            # 计算最小价格作为基准
            self.min_price = pf_data['price'].min()
            
            # 将价格转换为网格索引
            # 索引 i 对应的价格: P = min_price * (1 + box_size/100)^i
            # 反向: i = log(P/min_price) / log(1 + box_size/100)
            import numpy as np
            growth_rate = 1 + box_size / 100
            
            # 计算每个价格对应的网格索引
            pf_data['row_index'] = np.log(pf_data['price'] / self.min_price) / np.log(growth_rate)
            pf_data['row_index'] = pf_data['row_index'].round().astype(int)
            
            # 使用网格索引进行绘制
            self.custom_chart_item = CustomPFChartItem()
            self.custom_chart_item.set_data(pf_data, box_size, use_grid_index=True)
            self.plot_item.addItem(self.custom_chart_item)
            
            # 设置坐标范围（使用网格索引）
            x_data = pf_data['column'].values
            y_data = pf_data['row_index'].values
            
            x_min, x_max = x_data.min(), x_data.max()
            y_min, y_max = y_data.min(), y_data.max()
            
            # 设置范围并添加缓冲
            x_buffer = 0.5
            y_buffer = 0.5
            
            self.plot_item.setXRange(x_min - x_buffer, x_max + x_buffer)
            self.plot_item.setYRange(y_min - y_buffer, y_max + y_buffer)
            
            # 强制aspect ratio = 1，确保格子是正方形
            self.plot_item.setAspectLocked(True, 1.0)
            
            # 自定义Y轴刻度显示，将网格索引转换回价格
            self.plot_item.getAxis('left').setTicks(None)
            self.plot_item.getAxis('left').setTickSpacing(1, 0)
            self.growth_rate = growth_rate
            self.plot_item.getAxis('left').setTicks(self._get_price_ticks(y_min, y_max, growth_rate))
            
        else:
            # 点数类型，将价格映射到整数网格
            # 网格索引 = price / box_size
            # 这样每个格子都是 1x1 的正方形
            pf_data['row_index'] = (pf_data['price'] / box_size).round().astype(int)
            
            self.custom_chart_item = CustomPFChartItem()
            self.custom_chart_item.set_data(pf_data, box_size, use_grid_index=True)
            self.plot_item.addItem(self.custom_chart_item)
            
            x_data = pf_data['column'].values
            y_data = pf_data['row_index'].values
            
            x_min, x_max = x_data.min(), x_data.max()
            y_min, y_max = y_data.min(), y_data.max()
            
            # 设置范围并添加缓冲
            x_buffer = 0.5
            y_buffer = 0.5
            
            self.plot_item.setXRange(x_min - x_buffer, x_max + x_buffer)
            self.plot_item.setYRange(y_min - y_buffer, y_max + y_buffer)
            
            # 强制aspect ratio = 1，确保格子是正方形
            self.plot_item.setAspectLocked(True, 1.0)
            
            # 自定义Y轴刻度显示，将网格索引转换回价格
            self.plot_item.getAxis('left').setTicks(None)
            self.plot_item.getAxis('left').setTickSpacing(1, 0)
            self.plot_item.getAxis('left').setTicks(self._get_price_ticks_point(y_min, y_max, box_size))
    
    def _get_price_ticks_point(self, y_min, y_max, box_size):
        """生成Y轴刻度，将网格索引转换为价格显示（点数模式）
        
        参数:
            y_min: 最小网格索引
            y_max: 最大网格索引
            box_size: box size数值
            
        返回:
            刻度列表，格式为 [(索引, 价格标签), ...]
        """
        ticks = []
        # 根据当前显示范围动态调整刻度密度
        range_length = y_max - y_min
        # 目标显示约10个刻度
        step = max(1, int(range_length / 10))
        
        for i in range(int(y_min), int(y_max) + 1, step):
            price = i * box_size
            ticks.append((i, f"{price:.2f}"))
        
        return [ticks, []]
    
    def _get_price_ticks(self, y_min, y_max, growth_rate):
        """生成Y轴刻度，将网格索引转换为价格显示（百分比模式）"""
        import numpy as np
        
        ticks = []
        # 根据当前显示范围动态调整刻度密度
        range_length = y_max - y_min
        # 目标显示约10个刻度
        step = max(1, int(range_length / 10))
        
        for i in range(int(y_min), int(y_max) + 1, step):
            price = self.min_price * (growth_rate ** i)
            ticks.append((i, f"{price:.2f}"))
        
        return [ticks, []]
    
    def mouse_moved(self, evt):
        pos = evt[0]
        if self.plot_item.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_item.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            
            if hasattr(self, 'parent') and hasattr(self.parent(), 'update_status'):
                self.parent().update_status(f"Column: {x:.1f}, Price: {y:.2f}")
    
    def _update_drag_rect(self):
        """更新拖拽框选矩形"""
        if self.drag_start and self.drag_end and self.drag_rect_item:
            x1, y1 = self.drag_start.x(), self.drag_start.y()
            x2, y2 = self.drag_end.x(), self.drag_end.y()
            
            # 计算矩形的左上角和右下角
            left = min(x1, x2)
            right = max(x1, x2)
            top = max(y1, y2)
            bottom = min(y1, y2)
            
            # 更新矩形
            self.drag_rect_item.setRect(left, bottom, right - left, top - bottom)
            
            # 实时寻找最佳TR
            start_col = int(left)
            end_col = int(right)
            
            if self.pf_engine and self.pf_data is not None:
                tr = self.pf_engine.find_best_tr(self.pf_data, start_col, end_col)
                
                if tr:
                    # 创建或更新WyckoffTargetItem
                    if self.wyckoff_target_item is None:
                        self.wyckoff_target_item = WyckoffTargetItem()
                        self.plot_item.addItem(self.wyckoff_target_item)
                    
                    # 计算目标价格（看涨和看跌）
                    target_price_bullish = self.pf_engine.calculate_target_price(tr, 'bullish')
                    target_price_bearish = self.pf_engine.calculate_target_price(tr, 'bearish')
                    
                    # 更新WyckoffTargetItem，同时显示看涨和看跌预测线
                    self.wyckoff_target_item.update_structure(
                        tr, 
                        target_price_bullish,
                        target_price_bearish,
                        self.box_size,
                        self.box_size_type,
                        self.min_price,
                        self.growth_rate
                    )
                else:
                    # 没有找到TR，清除显示
                    if self.wyckoff_target_item:
                        self.wyckoff_target_item.clear()
    
    def on_range_changed(self):
        """当视图范围变化时更新轴刻度"""
        # 防抖处理：如果已有待处理的更新，则跳过
        if self._update_pending:
            return
        
        self._update_pending = True
        
        # 使用定时器延迟更新，避免频繁重绘
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, self._update_axis_ticks)
    
    def _update_axis_ticks(self):
        """延迟更新轴刻度"""
        self._update_pending = False
        
        # 获取当前视图范围
        x_range = self.plot_item.vb.viewRange()[0]
        y_range = self.plot_item.vb.viewRange()[1]
        
        # 更新Y轴刻度
        if self.box_size_type == 'percent' and self.growth_rate is not None:
            # 百分比模式
            ticks = []
            range_length = y_range[1] - y_range[0]
            step = max(1, int(range_length / 10))
            
            for i in range(int(y_range[0]), int(y_range[1]) + 1, step):
                price = self.min_price * (self.growth_rate ** i)
                ticks.append((i, f"{price:.2f}"))
            
            self.plot_item.getAxis('left').setTicks([ticks, []])
        elif self.box_size_type == 'point':
            # 点数模式
            ticks = []
            range_length = y_range[1] - y_range[0]
            step = max(1, int(range_length / 10))
            
            for i in range(int(y_range[0]), int(y_range[1]) + 1, step):
                price = i * self.box_size
                ticks.append((i, f"{price:.2f}"))
            
            self.plot_item.getAxis('left').setTicks([ticks, []])
    
    def mouse_moved(self, evt):
        pos = evt[0]
        if self.plot_item.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_item.vb.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            
            if hasattr(self, 'parent') and hasattr(self.parent(), 'update_status'):
                self.parent().update_status(f"Column: {x:.1f}, Price: {y:.2f}")
    
    def eventFilter(self, source, event):
        """事件过滤器，处理鼠标事件和键盘事件
        
        功能:
        - 处理鼠标拖拽框选（非手模式）
        - 处理窗口拖拽（手模式）
        - 处理H键切换手模式
        """
        # 处理键盘事件
        if event.type() == event.KeyPress:
            if event.key() == Qt.Key_H:
                # H键：切换手模式
                self.hand_mode = not self.hand_mode
                if self.hand_mode:
                    # 进入手模式：启用鼠标拖拽，禁用框选
                    self.plot_item.setMouseEnabled(x=True, y=True)
                    self.setCursor(Qt.OpenHandCursor)
                    if hasattr(self, 'parent') and hasattr(self.parent(), 'update_status'):
                        self.parent().update_status("手模式已启用（按H键切换）")
                else:
                    # 退出手模式：禁用鼠标拖拽，启用框选
                    self.plot_item.setMouseEnabled(x=False, y=False)
                    self.setCursor(Qt.ArrowCursor)
                    if hasattr(self, 'parent') and hasattr(self.parent(), 'update_status'):
                        self.parent().update_status("框选模式已启用（按H键切换）")
                return True
        
        if source == self.plot_item.scene():
            
            # 处理鼠标按下事件
            if event.type() == event.GraphicsSceneMousePress:
                if event.button() == Qt.LeftButton:
                    pos = event.scenePos()
                    if self.plot_item.sceneBoundingRect().contains(pos):
                        # 手模式：允许拖拽窗口
                        if self.hand_mode:
                            self.setCursor(Qt.ClosedHandCursor)
                            return False  # 让默认事件处理器处理拖拽
                        
                        # 非手模式：启用框选功能
                        mouse_point = self.plot_item.vb.mapSceneToView(pos)
                        self.drag_start = mouse_point
                        self.is_dragging = True
                        self.mouse_pressed = True
                        self.drag_end = mouse_point
                        
                        # 创建拖拽框选矩形
                        if self.drag_rect_item:
                            self.plot_item.removeItem(self.drag_rect_item)
                        
                        self.drag_rect_item = pg.QtWidgets.QGraphicsRectItem()
                        self.drag_rect_item.setPen(pg.mkPen('y', width=2, style=Qt.DashLine))
                        self.drag_rect_item.setBrush(pg.mkBrush(255, 255, 0, 50))
                        self.plot_item.addItem(self.drag_rect_item)
                        
                        # 更新矩形位置
                        self._update_drag_rect()
                        
                        return True
            
            # 处理鼠标释放事件
            elif event.type() == event.GraphicsSceneMouseRelease:
                if event.button() == Qt.LeftButton:
                    self.is_dragging = False
                    self.mouse_pressed = False
                    
                    # 手模式：恢复手型光标
                    if self.hand_mode:
                        self.setCursor(Qt.OpenHandCursor)
                    
                    return True
            
            # 处理鼠标移动事件
            elif event.type() == event.GraphicsSceneMouseMove:
                # 手模式：不处理框选
                if self.hand_mode:
                    return False
                
                # 非手模式：处理框选
                if self.is_dragging and self.mouse_pressed:
                    pos = event.scenePos()
                    if self.plot_item.sceneBoundingRect().contains(pos):
                        mouse_point = self.plot_item.vb.mapSceneToView(pos)
                        self.drag_end = mouse_point
                        self._update_drag_rect()
                    return True
            
            # 处理鼠标双击事件
            elif event.type() == event.GraphicsSceneMouseDoubleClick:
                if event.button() == Qt.RightButton:
                    # 右键双击，清除TR显示
                    if self.wyckoff_target_item:
                        self.wyckoff_target_item.clear()
                    return True
        
        return super().eventFilter(source, event)


class CustomPFChartItem(pg.GraphicsObject):
    def __init__(self):
        super().__init__()
        self.pf_data = None
        self.box_size = 1.0
        self.use_grid_index = False
        self.picture = None
        
        # 启用缓存以提升性能
        self.setCacheMode(self.DeviceCoordinateCache)
    
    def set_data(self, pf_data, box_size=1.0, use_grid_index=False):
        """设置数据并生成图形
        
        参数:
            pf_data: 包含column, type, price(或row_index)列的DataFrame
            box_size: box size数值
            use_grid_index: 是否使用网格索引（用于百分比类型）
        """
        self.pf_data = pf_data
        self.box_size = box_size
        self.use_grid_index = use_grid_index
        self.generate_picture()
    
    def generate_picture(self):
        """生成图形"""
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)
        
        if self.pf_data is not None and not self.pf_data.empty:
            for _, row in self.pf_data.iterrows():
                x = row['column']
                
                # 根据是否使用网格索引选择Y坐标
                if self.use_grid_index:
                    y = row['row_index']
                else:
                    y = row['price']
                
                # 计算格子边界
                # 使用网格索引时，每个格子都是1x1的正方形
                # X轴: 从 column - 0.5 到 column + 0.5
                # Y轴: 从 y - 0.5 到 y + 0.5
                x_left = x - 0.5
                x_right = x + 0.5
                y_bottom = y - 0.5
                y_top = y + 0.5
                
                if row['type'] == 'X':
                    # 绘制绿色X，填满整个格子
                    # 颜色定义: (0, 180, 0) 表示RGB颜色，0为红色通道，180为绿色通道，0为蓝色通道
                    # 这是一种鲜艳的绿色，常用于表示上涨信号
                    # 线条粗细: width=3 表示X的线条宽度为3像素
                    pen = pg.mkPen((0, 180, 0), width=2)
                    painter.setPen(pen)
                    # 从对角线绘制X
                    # 第一条对角线: 从格子左下角到右上角
                    painter.drawLine(x_left, y_bottom, x_right, y_top)
                    # 第二条对角线: 从格子左上角到右下角
                    painter.drawLine(x_left, y_top, x_right, y_bottom)
                else:
                    # 绘制红色空心O，填满整个格子
                    # 颜色定义: (255, 0, 0) 表示RGB颜色，255为红色通道，0为绿色通道，0为蓝色通道
                    # 这是一种鲜艳的红色，常用于表示下跌信号
                    # 线条粗细: width=4 表示O的线条宽度为4像素
                    # 比X的线条稍粗，使O在视觉上更加突出
                    pen = pg.mkPen((255, 0, 0), width=2)
                    painter.setPen(pen)
                    # 绘制椭圆，填满格子
                    # 使用drawEllipse函数绘制椭圆，参数分别为:
                    # x_left: 椭圆左上角X坐标
                    # y_bottom: 椭圆左上角Y坐标
                    # 1.0: 椭圆宽度（占满整个格子）
                    # 1.0: 椭圆高度（占满整个格子）
                    # 由于宽度和高度都是1.0，因此绘制的是一个正圆形
                    painter.drawEllipse(x_left, y_bottom, 1.0, 1.0)
        
        painter.end()
    
    def paint(self, painter, option, widget):
        """绘制图形"""
        if self.picture:
            painter.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        """返回图形边界"""
        if self.pf_data is None or self.pf_data.empty:
            return pg.QtCore.QRectF(0, 0, 1, 1)
        
        x_data = self.pf_data['column'].values
        
        # 根据是否使用网格索引选择Y数据
        if self.use_grid_index:
            y_data = self.pf_data['row_index'].values
            y_buffer = 0.5
        else:
            y_data = self.pf_data['price'].values
            y_buffer = self.box_size / 2
        
        x_min = x_data.min() - 0.5
        x_max = x_data.max() + 0.5
        y_min = y_data.min() - y_buffer
        y_max = y_data.max() + y_buffer
        
        return pg.QtCore.QRectF(x_min, y_min, x_max - x_min, y_max - y_min)


class WyckoffTargetItem(pg.GraphicsObject):
    """威科夫目标价预测组件
    
    功能:
    - 显示交易区间(TR)框
    - 显示目标价预测线（向上和向下）
    - 支持磁吸式交互
    """
    
    def __init__(self):
        super().__init__()
        self.tr_rect = None  # TR框 (QRectF)
        self.bullish_target_line = None  # 看涨预测线 (QLineF)
        self.bearish_target_line = None  # 看跌预测线 (QLineF)
        self.bullish_target_price = None  # 看涨目标价格
        self.bearish_target_price = None  # 看跌目标价格
        self.box_size = 1.0  # Box Size
        self.box_size_type = 'point'  # Box Size类型
        self.min_price = None  # 最小价格（百分比模式使用）
        self.growth_rate = None  # 增长率（百分比模式使用）
        self.picture = None  # 绘制图形
        
        # 设置图形标志，使其可以接收鼠标事件
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
        
        # 禁用缓存以避免更新延迟问题
        self.setCacheMode(self.NoCache)
    
    def update_structure(self, tr_object, bullish_target_price, bearish_target_price, box_size, box_size_type='point', min_price=None, growth_rate=None):
        """更新结构，根据磁吸结果更新自身位置
        
        参数:
            tr_object: TRObject对象，包含交易区间信息
            bullish_target_price: 看涨目标价格
            bearish_target_price: 看跌目标价格
            box_size: Box Size数值
            box_size_type: Box Size类型 ('point' 或 'percent')
            min_price: 最小价格（百分比模式使用）
            growth_rate: 增长率（百分比模式使用）
        """
        self.box_size = box_size
        self.box_size_type = box_size_type
        self.min_price = min_price
        self.growth_rate = growth_rate
        self.bullish_target_price = bullish_target_price
        self.bearish_target_price = bearish_target_price
        
        # 计算TR框的坐标
        # X轴: 从 start_idx - 0.5 到 end_idx + 0.5
        x_left = tr_object.start_idx - 0.5
        x_right = tr_object.end_idx + 0.5
        
        # Y轴: 根据Box Size类型转换价格到网格坐标
        if box_size_type == 'percent':
            # 百分比模式: 网格索引 = log(price / min_price) / log(growth_rate)
            import numpy as np
            y_bottom = np.log(tr_object.low / min_price) / np.log(growth_rate) - 0.5
            y_top = np.log(tr_object.high / min_price) / np.log(growth_rate) + 0.5
            bullish_target_y = np.log(bullish_target_price / min_price) / np.log(growth_rate)
            bearish_target_y = np.log(bearish_target_price / min_price) / np.log(growth_rate)
        else:
            # 点数模式: 网格索引 = price / box_size
            y_bottom = tr_object.low / box_size - 0.5
            y_top = tr_object.high / box_size + 0.5
            bullish_target_y = bullish_target_price / box_size
            bearish_target_y = bearish_target_price / box_size
        
        # 创建TR框
        self.tr_rect = QRectF(x_left, y_bottom, x_right - x_left, y_top - y_bottom)
        
        # 创建看涨预测线：从TR框右上角向上延伸，起点是TR框最高价
        # 看涨目标价 = TR_High + (列数 × BoxSize × Reversal)
        self.bullish_target_line = (QPointF(x_right, y_top), QPointF(x_right, bullish_target_y))
        
        # 创建看跌预测线：从TR框右下角向下延伸，起点是TR框最低价
        # 看跌目标价 = TR_Low - (列数 × BoxSize × Reversal)
        self.bearish_target_line = (QPointF(x_right, y_bottom), QPointF(x_right, bearish_target_y))
        
        # 重新生成图形
        self.generate_picture()
        
        # 更新边界
        #self.updateGeometry()
        
        # 触发重绘
        self.update()
    
    def generate_picture(self):
        """生成图形
        
        功能:
        - 绘制交易区间(TR)框，使用较细的蓝色边框
        - 绘制看涨目标价预测线（绿色虚线），从TR框右上角向上延伸
        - 绘制看跌目标价预测线（红色虚线），从TR框右下角向下延伸
        - 添加标签文本，使用合适的字体大小
        """
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)
        
        # 设置字体：使用Arial字体，大小为6
        font = painter.font()
        font.setFamily("times new roman")
        font.setPointSize(3) # 增大字体大小提升可读性
        painter.setFont(font)
        
        if self.tr_rect is not None:
            # 绘制TR框 - 只使用蓝色边框，不使用填充
            # 使用蓝色边框，线条粗细为0.5（较细）
            pen = QPen(QColor(0, 100, 255), 0.5)
            painter.setPen(pen)
            
            # 绘制矩形（不设置brush，即不填充）
            painter.drawRect(self.tr_rect)
            
            # 在TR框上方添加标签
            # 保存当前画布状态
            painter.save()
            # 翻转Y轴坐标系以修复字体倒置问题
            painter.scale(1, -1)
            # 使用黑色文字，线条粗细为1
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            label_text = f"TR (Cols: {int(self.tr_rect.width())})"
            # 文本位置：在TR框左上角上方5像素处（Y坐标需要取负）
            painter.drawText(self.tr_rect.left(), -self.tr_rect.top() - 5, label_text)
            # 恢复画布状态
            painter.restore()
        
        # 绘制看涨预测线（绿色虚线）
        if self.bullish_target_line is not None:
            start_point, end_point = self.bullish_target_line
            
            # 看涨: 绿色，线条粗细为1（较细）
            pen = QPen(QColor(0, 180, 0), 0.5)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(start_point, end_point)
            
            # 在目标价格处添加标签
            # 保存当前画布状态
            painter.save()
            # 翻转Y轴坐标系以修复字体倒置问题
            painter.scale(1, -1)
            # 使用黑色文字，线条粗细为1
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            label_text = f"Bull: {self.bullish_target_price:.2f}"
            # 文本位置：在预测线终点上方（Y坐标需要取负）
            painter.drawText(end_point.x() + 5, -end_point.y() - 5, label_text)
            # 恢复画布状态
            painter.restore()
        
        # 绘制看跌预测线（红色虚线）
        if self.bearish_target_line is not None:
            start_point, end_point = self.bearish_target_line
            
            # 看跌: 红色，线条粗细为1（较细）
            pen = QPen(QColor(255, 0, 0), 0.5)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(start_point, end_point)
            
            # 在目标价格处添加标签
            # 保存当前画布状态
            painter.save()
            # 翻转Y轴坐标系以修复字体倒置问题
            painter.scale(1, -1)
            # 使用黑色文字，线条粗细为1
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            label_text = f"Bear: {self.bearish_target_price:.2f}"
            # 文本位置：在预测线终点下方（Y坐标需要取负）
            painter.drawText(end_point.x() + 5, -end_point.y() + 10, label_text)
            # 恢复画布状态
            painter.restore()
        
        painter.end()
    
    def paint(self, painter, option, widget):
        """绘制图形"""
        if self.picture:
            painter.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        """返回图形边界"""
        if self.tr_rect is None:
            return QRectF(0, 0, 1, 1)
        
        # 返回TR框和预测线的并集边界
        rect = QRectF(self.tr_rect)
        
        # 扩展边界以包含看涨预测线
        if self.bullish_target_line is not None:
            start_point, end_point = self.bullish_target_line
            rect = rect.united(QRectF(start_point, end_point))
        
        # 扩展边界以包含看跌预测线
        if self.bearish_target_line is not None:
            start_point, end_point = self.bearish_target_line
            rect = rect.united(QRectF(start_point, end_point))
        
        # 添加一些缓冲
        rect.adjust(-10, -10, 10, 10)
        
        return rect
    
    def clear(self):
        """清除显示"""
        self.tr_rect = None
        self.bullish_target_line = None
        self.bearish_target_line = None
        self.bullish_target_price = None
        self.bearish_target_price = None
        self.picture = None
        self.update()
