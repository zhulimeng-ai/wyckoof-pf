import sys
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QComboBox, QDoubleSpinBox, 
                             QLabel, QFileDialog, QStatusBar, QSplitter, QAction)
from PyQt5.QtCore import Qt
from src.ui.pf_chart import PFChartWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wyckoff Point & Figure Chart v0.2")
        self.setGeometry(100, 100, 1400, 900)
        
        self.data = None
        self.pf_data = None
        self.selected_column = None  # 用户选择的数据列
        self.current_box_type = 'point'  # 当前box_size类型
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 创建分割器，左侧控制面板，右侧图表
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = self.create_control_panel()
        right_panel = self.create_chart_panel()
        
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 1400]) # 控制面板宽度为200，图表宽度为1400
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def create_control_panel(self) -> QWidget:
        """创建左侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        title_label = QLabel("控制面板")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        layout.addSpacing(20)
        
        # 数据导入部分
        file_label = QLabel("數據導入:")
        layout.addWidget(file_label)
        
        self.import_btn = QPushButton("導入 CSV/Parquet")
        self.import_btn.clicked.connect(self.import_data)
        layout.addWidget(self.import_btn)
        
        layout.addSpacing(10)
        
        # 添加列选择下拉框
        column_label = QLabel("選擇數據列:")
        layout.addWidget(column_label)
        
        self.column_combo = QComboBox()
        self.column_combo.setEnabled(False)  # 初始禁用，导入数据后启用
        self.column_combo.currentTextChanged.connect(self.on_column_changed)
        layout.addWidget(self.column_combo)
        
        layout.addSpacing(20)
        
        # Box Size 参数设置部分
        box_type_label = QLabel("Box Size 類型:")
        layout.addWidget(box_type_label)
        
        self.box_type_combo = QComboBox()
        self.box_type_combo.addItems(["point", "percent"])
        layout.addWidget(self.box_type_combo)
        
        layout.addSpacing(10)
        
        box_size_label = QLabel("Box Size 數值:")
        layout.addWidget(box_size_label)
        
        self.box_size_spin = QDoubleSpinBox()
        self.box_size_spin.setRange(0.01, 10000)
        self.box_size_spin.setValue(1.0)
        self.box_size_spin.setSingleStep(0.1)
        self.box_size_spin.setDecimals(2)
        layout.addWidget(self.box_size_spin)
        
        layout.addSpacing(10)
        
        reversal_label = QLabel("Reversal (格):")
        layout.addWidget(reversal_label)
        
        self.reversal_spin = QDoubleSpinBox()
        self.reversal_spin.setRange(1, 20)
        self.reversal_spin.setValue(3)
        self.reversal_spin.setDecimals(0)
        layout.addWidget(self.reversal_spin)
        
        layout.addSpacing(20)
        
        self.calculate_btn = QPushButton("計算並繪製")
        self.calculate_btn.clicked.connect(self.calculate_and_draw)
        self.calculate_btn.setEnabled(False)
        layout.addWidget(self.calculate_btn)
        
        layout.addSpacing(20)
        
        # TR识别模式按钮（预留功能）
        tr_mode_label = QLabel("TR 識別模式:")
        layout.addWidget(tr_mode_label)
        
        self.fixed_tr_btn = QPushButton("固定TR識別")
        self.fixed_tr_btn.setEnabled(False)  # 暂时禁用，预留功能
        layout.addWidget(self.fixed_tr_btn)
        
        self.manual_tr_btn = QPushButton("手動TR識別")
        self.manual_tr_btn.setEnabled(False)  # 暂时禁用，预留功能
        layout.addWidget(self.manual_tr_btn)
        
        layout.addStretch()
        
        # 说明文字
        info_label = QLabel("說明:\n\n1. 導入包含日期和數值\n   字段的數據文件\n2. 選擇要使用的數據列\n3. 設置 Box Size 參數\n4. 點擊計算並繪製\n\n支持格式: CSV, Parquet\n\n提示:\n- 系統會自動選擇\n  'Close' 或 'Price' 列\n- 您可以手動選擇\n  其他數值列")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)
        
        return panel
    
    def create_chart_panel(self) -> QWidget:
        """创建右侧图表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 创建图表组件
        self.chart_widget = PFChartWidget()
        
        layout.addWidget(self.chart_widget)
        
        return panel
    
    def import_data(self):
        """导入CSV或Parquet文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇數據文件", "", 
            "CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)"
        )
        
        if file_path:
            try:
                # 根据文件扩展名读取数据
                if file_path.endswith('.csv'):
                    self.data = pd.read_csv(file_path)
                elif file_path.endswith('.parquet'):
                    self.data = pd.read_parquet(file_path)
                else:
                    self.status_bar.showMessage("不支持的文件格式")
                    return
                
                # 自动检测日期列
                date_col = None
                for col in self.data.columns:
                    if col.lower() in ['date', 'timestamp', 'datetime']:
                        date_col = col
                        break
                
                if date_col is None:
                    self.status_bar.showMessage("文件中缺少日期列 (Date/Timestamp/Datetime)")
                    return
                
                # 设置日期列为索引
                self.data[date_col] = pd.to_datetime(self.data[date_col])
                self.data = self.data.sort_values(date_col)
                self.data.set_index(date_col, inplace=True)
                
                # 填充列选择下拉框
                self.column_combo.clear()
                numeric_columns = self.data.select_dtypes(include=['number']).columns.tolist()
                
                if not numeric_columns:
                    self.status_bar.showMessage("文件中没有数值列")
                    return
                
                self.column_combo.addItems(numeric_columns)
                self.column_combo.setEnabled(True)
                
                # 自动选择默认列（优先选择close或price列）
                default_col = None
                for col in numeric_columns:
                    if col.lower() in ['close', 'price']:
                        default_col = col
                        break
                
                if default_col:
                    self.column_combo.setCurrentText(default_col)
                else:
                    self.column_combo.setCurrentIndex(0)
                
                self.calculate_btn.setEnabled(True)
                self.status_bar.showMessage(f"成功導入 {len(self.data)} 行數據")
                
            except Exception as e:
                self.status_bar.showMessage(f"導入失敗: {str(e)}")
    
    def on_column_changed(self, column_name):
        """当用户选择不同的列时触发"""
        self.selected_column = column_name
        self.status_bar.showMessage(f"已選擇列: {column_name}")
    
    def calculate_and_draw(self):
        """计算并绘制Point & Figure图表"""
        if self.data is None:
            self.status_bar.showMessage("請先導入數據")
            return
        
        # 检查是否已选择列
        if self.selected_column is None:
            self.status_bar.showMessage("請先選擇數據列")
            return
        
        from src.pf_engine import PFEngine
        
        box_type = self.box_type_combo.currentText()
        box_size = self.box_size_spin.value()
        reversal = int(self.reversal_spin.value())
        
        # 保存当前的box_size_type，用于绘图
        self.current_box_type = box_type
        
        # 创建引擎并计算
        engine = PFEngine(box_size_type=box_type, box_size_value=box_size, reversal=reversal)
        
        # 将引擎传递给图表组件
        self.chart_widget.pf_engine = engine
        
        # 使用用户选择的列
        self.pf_data = engine.calculate_pf_dataframe(self.data[self.selected_column])
        
        if self.pf_data.empty:
            self.status_bar.showMessage("計算結果為空，請調整參數")
            return
        
        # 将点数图数据传递给图表组件
        self.chart_widget.pf_data = self.pf_data
        
        self.draw_chart()
        self.status_bar.showMessage(f"計算完成，共 {len(self.pf_data)} 個方格")
    
    def draw_chart(self):
        """绘制Point & Figure图表"""
        box_size = self.box_size_spin.value()
        # 传递box_size_type参数
        box_type = getattr(self, 'current_box_type', 'point')
        self.chart_widget.plot_pf_data(self.pf_data, box_size, box_type)
    
    def update_status(self, message: str):
        """更新状态栏消息"""
        self.status_bar.showMessage(message)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
