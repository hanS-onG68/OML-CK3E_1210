#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import numpy as np
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import pyqtgraph as pg
from datetime import datetime

# ============ 数据管理类 ============
class AmplifierSystem:
    def __init__(self):
        self.num_amplifiers = 19
        self.channels_per_amp = 8
        self.buffer_size = 1024
        
        # 初始化数据缓冲区
        self.data_buffers = {}
        for amp in range(19):
            for ch in range(8):
                key = f'AMP{amp+1}_CH{ch+1}'
                self.data_buffers[key] = np.zeros(self.buffer_size)
        
        # 通道状态：'normal', 'abnormal', 'testing', 'passed', 'failed'
        self.channel_status = {key: 'normal' for key in self.data_buffers.keys()}
        
        # 测试结果记录
        self.test_results = {}

# ============ 数据采集线程 ============
class DataAcquisitionThread(QThread):
    data_updated = Signal(dict)
    
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.running = False
        self.sample_count = 0
        self.test_mode = False
        self.test_channel = None
        self.test_signal_type = 'sine'
    
    def run(self):
        self.running = True
        while self.running:
            data = {}
            for amp in range(19):
                for ch in range(8):
                    key = f'AMP{amp+1}_CH{ch+1}'
                    
                    if self.test_mode and key == self.test_channel:
                        value = self.generate_test_signal()
                    else:
                        t = self.sample_count * 0.01
                        freq = 0.5 + (amp * 8 + ch) * 0.05
                        value = 2.5 + 0.5 * np.sin(2 * np.pi * freq * t) + 0.05 * np.random.randn()
                    
                    data[key] = value
            
            self.sample_count += 1
            self.data_updated.emit(data)
            self.msleep(10)
    
    def generate_test_signal(self):
        t = self.sample_count * 0.01
        
        if self.test_signal_type == 'sine':
            return 2.5 + 1.0 * np.sin(2 * np.pi * 1.0 * t)
        elif self.test_signal_type == 'square':
            return 2.5 + 1.0 * np.sign(np.sin(2 * np.pi * 0.5 * t))
        elif self.test_signal_type == 'step':
            return 2.5 + 1.0 if t % 4 < 2 else 2.5 - 1.0
        else:
            return 2.5 + 0.5 * np.sin(2 * np.pi * 1.0 * t)
    
    def start_test(self, channel_key, signal_type='sine'):
        self.test_mode = True
        self.test_channel = channel_key
        self.test_signal_type = signal_type
        self.sample_count = 0
    
    def stop_test(self):
        self.test_mode = False
        self.test_channel = None
    
    def stop(self):
        self.running = False
        self.wait()

# ============ 选择测试通道对话框 ============
class SelectChannelsDialog(QDialog):
    """选择要测试的通道"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.selected_channels = []
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("选择测试通道")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("请选择要测试的通道")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 全选/取消全选按钮
        select_layout = QHBoxLayout()
        self.btn_select_all = QPushButton('✓ 全选')
        self.btn_select_all.clicked.connect(self.select_all)
        select_layout.addWidget(self.btn_select_all)
        
        self.btn_deselect_all = QPushButton('✗ 取消全选')
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        select_layout.addWidget(self.btn_deselect_all)
        
        self.btn_select_abnormal = QPushButton('⚠️ 选择异常通道')
        self.btn_select_abnormal.clicked.connect(self.select_abnormal)
        select_layout.addWidget(self.btn_select_abnormal)
        
        layout.addLayout(select_layout)
        
        # 快捷选择
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("快捷选择:"))
        
        for amp in range(1, 20):
            btn = QPushButton(f"AMP{amp}")
            btn.clicked.connect(lambda checked, a=amp: self.select_amplifier(a))
            btn.setFixedWidth(40)
            quick_layout.addWidget(btn)
            if amp % 10 == 0:
                quick_layout.addWidget(QLabel(""))
        
        layout.addLayout(quick_layout)
        
        # 通道列表（带复选框）
        self.channel_list = QListWidget()
        self.channel_list.setSelectionMode(QListWidget.MultiSelection)
        
        # 添加所有通道
        for amp in range(19):
            for ch in range(8):
                key = f'AMP{amp+1}_CH{ch+1}'
                item = QListWidgetItem(f"放大器{amp+1} - 通道{ch+1}")
                item.setData(Qt.UserRole, key)
                
                # 显示当前状态
                status = self.parent_window.system.channel_status.get(key, 'normal')
                if status == 'abnormal' or status == 'failed':
                    item.setBackground(QColor(255, 200, 200))
                    item.setToolTip("该通道异常，建议测试")
                elif status == 'testing':
                    item.setBackground(QColor(200, 200, 255))
                elif status == 'passed':
                    item.setBackground(QColor(200, 255, 200))
                    item.setToolTip("该通道已通过测试")
                
                self.channel_list.addItem(item)
        
        layout.addWidget(self.channel_list)
        
        # 统计信息
        self.stats_label = QLabel("已选择: 0 个通道")
        self.stats_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.stats_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.btn_test = QPushButton('▶ 开始测试')
        self.btn_test.clicked.connect(self.start_test)
        self.btn_test.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_test)
        
        self.btn_cancel = QPushButton('✕ 取消')
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # 更新统计
        self.channel_list.itemSelectionChanged.connect(self.update_stats)
    
    def select_all(self):
        """全选"""
        for i in range(self.channel_list.count()):
            self.channel_list.item(i).setSelected(True)
    
    def deselect_all(self):
        """取消全选"""
        for i in range(self.channel_list.count()):
            self.channel_list.item(i).setSelected(False)
    
    def select_abnormal(self):
        """选择异常通道"""
        self.deselect_all()
        for i in range(self.channel_list.count()):
            item = self.channel_list.item(i)
            key = item.data(Qt.UserRole)
            status = self.parent_window.system.channel_status.get(key, 'normal')
            if status in ['abnormal', 'failed']:
                item.setSelected(True)
    
    def select_amplifier(self, amp_num):
        """选择某个放大器的所有通道"""
        self.deselect_all()
        for i in range(self.channel_list.count()):
            item = self.channel_list.item(i)
            key = item.data(Qt.UserRole)
            if key.startswith(f'AMP{amp_num}_'):
                item.setSelected(True)
    
    def update_stats(self):
        """更新统计信息"""
        count = len(self.channel_list.selectedItems())
        self.stats_label.setText(f"已选择: {count} 个通道")
        self.btn_test.setEnabled(count > 0)
    
    def start_test(self):
        """开始测试"""
        selected_items = self.channel_list.selectedItems()
        self.selected_channels = [item.data(Qt.UserRole) for item in selected_items]
        
        if not self.selected_channels:
            QMessageBox.warning(self, "警告", "请至少选择一个通道")
            return
        
        self.close()

# ============ 单通道测试对话框 ============
class ChannelTestDialog(QDialog):
    """单通道测试对话框"""
    
    def __init__(self, parent=None, channel_key=None):
        super().__init__(parent)
        self.channel_key = channel_key
        self.parent_window = parent
        self.test_running = False
        self.test_data = []
        self.time_data = []
        self.start_time = None
        
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"通道测试 - {self.channel_key}")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # 通道信息
        info_group = QGroupBox("通道信息")
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"<b>通道:</b> {self.channel_key}"))
        
        # 显示状态
        self.status_indicator = QLabel("⚪ 就绪")
        self.status_indicator.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.status_indicator)
        
        info_layout.addStretch()
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 测试信号设置
        signal_group = QGroupBox("测试信号设置")
        signal_layout = QGridLayout()
        
        signal_layout.addWidget(QLabel("信号类型:"), 0, 0)
        self.signal_combo = QComboBox()
        self.signal_combo.addItems(['正弦波 (Sine)', '方波 (Square)', '阶跃 (Step)'])
        signal_layout.addWidget(self.signal_combo, 0, 1)
        
        signal_layout.addWidget(QLabel("幅值 (V):"), 1, 0)
        self.amp_spin = QDoubleSpinBox()
        self.amp_spin.setRange(0.1, 5.0)
        self.amp_spin.setValue(1.0)
        self.amp_spin.setSingleStep(0.1)
        signal_layout.addWidget(self.amp_spin, 1, 1)
        
        signal_layout.addWidget(QLabel("频率 (Hz):"), 2, 0)
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(0.1, 10.0)
        self.freq_spin.setValue(1.0)
        self.freq_spin.setSingleStep(0.1)
        signal_layout.addWidget(self.freq_spin, 2, 1)
        
        signal_layout.addWidget(QLabel("测试时长 (秒):"), 3, 0)
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(5)
        self.duration_spin.setSingleStep(1)
        signal_layout.addWidget(self.duration_spin, 3, 1)
        
        signal_group.setLayout(signal_layout)
        layout.addWidget(signal_group)
        
        # 波形显示
        plot_group = QGroupBox("测试波形")
        plot_layout = QVBoxLayout()
        self.test_plot = pg.PlotWidget()
        self.test_plot.setLabel('left', '电压', units='V')
        self.test_plot.setLabel('bottom', '时间', units='s')
        self.test_plot.setTitle('通道测试 - 实时波形')
        self.test_plot.showGrid(x=True, y=True, alpha=0.3)
        self.test_plot.setBackground('w')
        
        self.ref_curve = self.test_plot.plot(pen=pg.mkPen(color='#3498db', width=2, style=Qt.DashLine))
        self.meas_curve = self.test_plot.plot(pen=pg.mkPen(color='#e74c3c', width=3))
        
        plot_layout.addWidget(self.test_plot)
        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)
        
        # 测量结果显示
        result_group = QGroupBox("测量结果")
        result_layout = QGridLayout()
        
        self.lbl_max = QLabel("最大值: --")
        self.lbl_min = QLabel("最小值: --")
        self.lbl_avg = QLabel("平均值: --")
        self.lbl_pp = QLabel("峰峰值: --")
        self.lbl_rms = QLabel("有效值: --")
        self.lbl_freq = QLabel("频率: --")
        self.lbl_status = QLabel("状态: 等待测试")
        self.lbl_progress = QLabel("进度: 0%")
        
        result_layout.addWidget(self.lbl_max, 0, 0)
        result_layout.addWidget(self.lbl_min, 0, 1)
        result_layout.addWidget(self.lbl_avg, 0, 2)
        result_layout.addWidget(self.lbl_pp, 1, 0)
        result_layout.addWidget(self.lbl_rms, 1, 1)
        result_layout.addWidget(self.lbl_freq, 1, 2)
        result_layout.addWidget(self.lbl_status, 2, 0, 1, 2)
        result_layout.addWidget(self.lbl_progress, 2, 2)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.btn_start = QPushButton('▶ 开始测试')
        self.btn_start.clicked.connect(self.start_test)
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton('⏹ 停止测试')
        self.btn_stop.clicked.connect(self.stop_test)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        btn_layout.addWidget(self.btn_stop)
        
        self.btn_export = QPushButton('📊 导出报告')
        self.btn_export.clicked.connect(self.export_report)
        self.btn_export.setEnabled(False)
        btn_layout.addWidget(self.btn_export)
        
        self.btn_close = QPushButton('✕ 关闭')
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.setInterval(50)
    
    def start_test(self):
        if not self.parent_window:
            return
        
        # 获取参数
        signal_type = self.signal_combo.currentText()
        if '正弦' in signal_type:
            sig_type = 'sine'
        elif '方波' in signal_type:
            sig_type = 'square'
        else:
            sig_type = 'step'
        
        self.parent_window.start_channel_test(self.channel_key, sig_type)
        
        self.test_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        
        self.test_data = []
        self.time_data = []
        self.start_time = datetime.now()
        self.duration = self.duration_spin.value()
        
        self.status_indicator.setText("🔵 测试中...")
        self.status_indicator.setStyleSheet("color: blue; font-weight: bold;")
        self.lbl_status.setText("状态: 🔵 测试中...")
        self.lbl_status.setStyleSheet("color: blue; font-weight: bold;")
        
        self.update_timer.start()
    
    def stop_test(self):
        if self.parent_window:
            self.parent_window.stop_channel_test()
        
        self.test_running = False
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(True)
        
        self.status_indicator.setText("⏹ 测试完成")
        self.status_indicator.setStyleSheet("color: green; font-weight: bold;")
        self.lbl_progress.setText("进度: 100%")
        
        self.update_timer.stop()
        self.calculate_results()
    
    def update_display(self):
        if not self.parent_window:
            return
        
        buffer = self.parent_window.system.data_buffers.get(self.channel_key)
        if buffer is None:
            return
        
        # 更新波形
        ref_signal = self.generate_reference_signal(len(buffer))
        self.ref_curve.setData(ref_signal)
        self.meas_curve.setData(buffer)
        
        if len(buffer) > 0:
            max_val = np.max(buffer)
            min_val = np.min(buffer)
            range_val = max(max_val - min_val, 0.5)
            self.test_plot.setYRange(min_val - range_val*0.2, max_val + range_val*0.2)
        
        # 保存数据
        if len(buffer) > 0:
            self.test_data.append(buffer[-1])
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.time_data.append(elapsed)
            
            if len(self.test_data) > 1000:
                self.test_data = self.test_data[-1000:]
                self.time_data = self.time_data[-1000:]
            
            # 更新进度
            progress = min(100, int(elapsed / self.duration * 100))
            self.lbl_progress.setText(f"进度: {progress}%")
            
            # 自动停止
            if elapsed >= self.duration:
                self.stop_test()
    
    def generate_reference_signal(self, length):
        signal_type = self.signal_combo.currentText()
        amp = self.amp_spin.value()
        freq = self.freq_spin.value()
        
        t = np.linspace(0, length * 0.01, length)
        
        if '正弦' in signal_type:
            return 2.5 + amp * np.sin(2 * np.pi * freq * t)
        elif '方波' in signal_type:
            return 2.5 + amp * np.sign(np.sin(2 * np.pi * freq * t))
        else:
            return 2.5 + amp * (t % (1/freq) > 0.5/freq)
    
    def calculate_results(self):
        if len(self.test_data) < 10:
            self.lbl_status.setText("状态: ❌ 数据不足")
            return
        
        data = np.array(self.test_data)
        
        max_val = np.max(data)
        min_val = np.min(data)
        avg_val = np.mean(data)
        pp_val = max_val - min_val
        rms_val = np.sqrt(np.mean(data**2))
        
        # 频率检测
        zero_crossings = np.where(np.diff(np.sign(data - np.mean(data))))[0]
        if len(zero_crossings) > 2:
            freq = len(zero_crossings) / (2 * len(data) * 0.01)
        else:
            freq = 0
        
        self.lbl_max.setText(f"最大值: {max_val:.3f} V")
        self.lbl_min.setText(f"最小值: {min_val:.3f} V")
        self.lbl_avg.setText(f"平均值: {avg_val:.3f} V")
        self.lbl_pp.setText(f"峰峰值: {pp_val:.3f} V")
        self.lbl_rms.setText(f"有效值: {rms_val:.3f} V")
        self.lbl_freq.setText(f"频率: {freq:.2f} Hz")
        
        # 判断结果
        expected_amp = self.amp_spin.value()
        expected_freq = self.freq_spin.value()
        
        amp_error = abs(pp_val/2 - expected_amp) / expected_amp if expected_amp > 0 else 1
        freq_error = abs(freq - expected_freq) / expected_freq if expected_freq > 0 else 1
        
        if amp_error < 0.1 and freq_error < 0.1:
            status = "✅ 通过"
            color = "green"
            status_code = 'passed'
        elif amp_error < 0.2 and freq_error < 0.2:
            status = "⚠️ 边缘"
            color = "orange"
            status_code = 'marginal'
        else:
            status = "❌ 失败"
            color = "red"
            status_code = 'failed'
        
        self.lbl_status.setText(f"状态: {status} (幅值误差: {amp_error*100:.1f}%, 频率误差: {freq_error*100:.1f}%)")
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        # 更新系统状态
        if self.parent_window:
            self.parent_window.system.channel_status[self.channel_key] = status_code
            self.parent_window.update_channel_indicator(self.channel_key, status_code)
        
        self.test_results = {
            'channel': self.channel_key,
            'max': max_val,
            'min': min_val,
            'avg': avg_val,
            'pp': pp_val,
            'rms': rms_val,
            'freq': freq,
            'status': status,
            'status_code': status_code,
            'amp_error': amp_error,
            'freq_error': freq_error
        }
    
    def export_report(self):
        if not hasattr(self, 'test_results'):
            QMessageBox.warning(self, "警告", "没有测试结果可导出")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存测试报告",
            f"{self.channel_key}_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "文本文件 (*.txt);;CSV文件 (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("=" * 60 + "\n")
                    f.write(f"通道测试报告\n")
                    f.write(f"通道: {self.channel_key}\n")
                    f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 60 + "\n\n")
                    
                    f.write("测试参数:\n")
                    f.write(f"  信号类型: {self.signal_combo.currentText()}\n")
                    f.write(f"  幅值: {self.amp_spin.value()} V\n")
                    f.write(f"  频率: {self.freq_spin.value()} Hz\n")
                    f.write(f"  测试时长: {self.duration_spin.value()} 秒\n\n")
                    
                    f.write("测量结果:\n")
                    f.write(f"  最大值: {self.test_results['max']:.3f} V\n")
                    f.write(f"  最小值: {self.test_results['min']:.3f} V\n")
                    f.write(f"  平均值: {self.test_results['avg']:.3f} V\n")
                    f.write(f"  峰峰值: {self.test_results['pp']:.3f} V\n")
                    f.write(f"  有效值: {self.test_results['rms']:.3f} V\n")
                    f.write(f"  频率: {self.test_results['freq']:.2f} Hz\n\n")
                    
                    f.write(f"测试结论: {self.test_results['status']}\n")
                    f.write(f"幅值误差: {self.test_results['amp_error']*100:.1f}%\n")
                    f.write(f"频率误差: {self.test_results['freq_error']*100:.1f}%\n")
                
                QMessageBox.information(self, "成功", f"报告已保存到:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")
    
    def closeEvent(self, event):
        if self.test_running:
            self.stop_test()
        event.accept()

# ============ 批量测试线程 ============
class BatchTestThread(QThread):
    progress_updated = Signal(int, int, str, str)
    finished = Signal(list)
    
    def __init__(self, parent, channels):
        super().__init__(parent)
        self.parent = parent
        self.channels = channels
        self.results = []
    
    def run(self):
        for i, channel_key in enumerate(self.channels):
            # 开始测试
            self.parent.acquisition_thread.start_test(channel_key, 'sine')
            self.progress_updated.emit(i + 1, len(self.channels), channel_key, "测试中...")
            
            # 测试5秒
            self.msleep(5000)
            
            # 停止测试
            self.parent.acquisition_thread.stop_test()
            
            # 分析结果
            data = self.parent.system.data_buffers[channel_key]
            pp_val = np.max(data) - np.min(data)
            
            if 1.8 < pp_val < 2.2:
                status = "✅ 通过"
                status_code = 'passed'
            else:
                status = "❌ 失败"
                status_code = 'failed'
            
            self.parent.system.channel_status[channel_key] = status_code
            self.parent.update_channel_indicator(channel_key, status_code)
            
            self.results.append({
                'channel': channel_key,
                'pp': pp_val,
                'status': status,
                'status_code': status_code
            })
            
            self.progress_updated.emit(i + 1, len(self.channels), channel_key, status)
            
            # 间隔0.5秒
            self.msleep(500)
        
        self.finished.emit(self.results)

# ============ 主窗口类 ============
class MultiAmplifierMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.system = AmplifierSystem()
        self.acquisition_thread = DataAcquisitionThread(self.system)
        self.acquisition_thread.data_updated.connect(self.on_data_received)
        
        self.is_running = False
        self.sample_count = 0
        self.test_dialog = None
        self.batch_thread = None
        
        self.init_ui()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # 左侧：控制面板
        left_panel = self.create_control_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 右侧：Tab显示区
        right_panel = self.create_tab_area()
        main_layout.addWidget(right_panel, 4)
        
        self.setWindowTitle("19放大器（152通道）实时监控系统 - 可选择通道测试")
        self.resize(1600, 900)
        
        self.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 2px solid #ccc; 
                border-radius: 5px; 
                margin-top: 10px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px 0 5px; 
            }
            QPushButton { 
                padding: 8px; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #e0e0e0; 
            }
            QTabWidget::pane { 
                border: 1px solid #ccc; 
            }
            QTabBar::tab { 
                padding: 8px 15px; 
            }
            QTabBar::tab:selected { 
                background-color: #4CAF50; 
                color: white; 
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
        """)
    
    def create_control_panel(self):
        panel = QGroupBox("控制面板")
        layout = QVBoxLayout()
        
        # 采集控制
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton('▶ 开始采集')
        self.btn_start.clicked.connect(self.start_acquisition)
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_layout.addWidget(self.btn_start)
        
        self.btn_stop = QPushButton('⏹ 停止采集')
        self.btn_stop.clicked.connect(self.stop_acquisition)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #f44336; color: white;")
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)
        
        layout.addSpacing(10)
        
        # 测试控制
        test_group = QGroupBox("通道测试")
        test_layout = QVBoxLayout()
        
        self.btn_select_test = QPushButton('🔬 选择通道测试')
        self.btn_select_test.clicked.connect(self.show_select_channels)
        self.btn_select_test.setStyleSheet("background-color: #2196F3; color: white;")
        test_layout.addWidget(self.btn_select_test)
        
        self.btn_batch_test = QPushButton('⚡ 快速批量测试 (所有通道)')
        self.btn_batch_test.clicked.connect(self.batch_test_all)
        self.btn_batch_test.setStyleSheet("background-color: #FF9800; color: white;")
        test_layout.addWidget(self.btn_batch_test)
        
        self.btn_test_abnormal = QPushButton('⚠️ 测试异常通道')
        self.btn_test_abnormal.clicked.connect(self.test_abnormal_channels)
        self.btn_test_abnormal.setStyleSheet("background-color: #e74c3c; color: white;")
        test_layout.addWidget(self.btn_test_abnormal)
        
        test_group.setLayout(test_layout)
        layout.addWidget(test_group)
        
        layout.addSpacing(10)
        
        # 数据保存
        self.btn_save = QPushButton('💾 保存数据')
        self.btn_save.clicked.connect(self.save_data)
        layout.addWidget(self.btn_save)
        
        layout.addSpacing(10)
        
        # 进度条
        layout.addWidget(QLabel("采集进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        layout.addSpacing(5)
        
        # 测试进度条
        layout.addWidget(QLabel("测试进度:"))
        self.test_progress_bar = QProgressBar()
        self.test_progress_bar.setRange(0, 100)
        layout.addWidget(self.test_progress_bar)
        
        layout.addSpacing(10)
        
        # 状态信息
        self.status_label = QLabel("🟡 就绪")
        self.status_label.setStyleSheet("font-size: 12px; padding: 5px;")
        layout.addWidget(self.status_label)
        
        self.test_status_label = QLabel("测试状态: 无")
        self.test_status_label.setStyleSheet("font-size: 12px; padding: 5px; color: gray;")
        layout.addWidget(self.test_status_label)
        
        # 统计信息
        stats_group = QGroupBox("通道统计")
        stats_layout = QGridLayout()
        
        self.stats_total = QLabel("总通道: 152")
        self.stats_passed = QLabel("✅ 通过: 0")
        self.stats_failed = QLabel("❌ 失败: 0")
        self.stats_untested = QLabel("⚪ 未测试: 152")
        
        stats_layout.addWidget(self.stats_total, 0, 0)
        stats_layout.addWidget(self.stats_passed, 0, 1)
        stats_layout.addWidget(self.stats_failed, 1, 0)
        stats_layout.addWidget(self.stats_untested, 1, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def create_tab_area(self):
        self.tab_widget = QTabWidget()
        
        overview_tab = self.create_overview_tab()
        self.tab_widget.addTab(overview_tab, "📊 概览")
        
        self.amp_tabs = []
        for i in range(19):
            tab = self.create_amplifier_tab(i)
            self.tab_widget.addTab(tab, f"放大器 {i+1}")
            self.amp_tabs.append(tab)
        
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        return self.tab_widget
    
    def create_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 统计信息
        stats_layout = QHBoxLayout()
        self.lbl_total = QLabel("总通道: 152")
        self.lbl_total.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.lbl_total)
        
        self.lbl_passed = QLabel("✅ 通过: 0")
        self.lbl_passed.setStyleSheet("color: green; font-weight: bold;")
        stats_layout.addWidget(self.lbl_passed)
        
        self.lbl_failed = QLabel("❌ 失败: 0")
        self.lbl_failed.setStyleSheet("color: red; font-weight: bold;")
        stats_layout.addWidget(self.lbl_failed)
        
        self.lbl_testing = QLabel("🔵 测试中: 0")
        self.lbl_testing.setStyleSheet("color: blue; font-weight: bold;")
        stats_layout.addWidget(self.lbl_testing)
        
        self.lbl_untested = QLabel("⚪ 未测试: 152")
        self.lbl_untested.setStyleSheet("color: gray; font-weight: bold;")
        stats_layout.addWidget(self.lbl_untested)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # 网格显示
        scroll_area = QScrollArea()
        grid_widget = QWidget()
        self.overview_grid = QGridLayout(grid_widget)
        self.overview_grid.setSpacing(2)
        self.channel_indicators = []
        
        for i in range(152):
            label = QLabel(f"{i+1}")
            label.setFixedSize(45, 30)
            label.setStyleSheet("""
                QLabel {
                    background-color: #95a5a6; 
                    border: 1px solid #333; 
                    color: white;
                    font-weight: bold;
                    border-radius: 3px;
                }
            """)
            label.setAlignment(Qt.AlignCenter)
            label.setToolTip(f"通道 {i+1}\n双击开始测试")
            label.mouseDoubleClickEvent = lambda e, idx=i: self.start_single_test(f'AMP{idx//8+1}_CH{idx%8+1}')
            self.overview_grid.addWidget(label, i//19, i%19)
            self.channel_indicators.append(label)
        
        scroll_area.setWidget(grid_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        tab.setLayout(layout)
        return tab
    
    def create_amplifier_tab(self, amp_index):
        tab = QWidget()
        layout = QVBoxLayout()
        
        # 通道数值显示
        grid_layout = QGridLayout()
        self.amp_value_labels = {}
        
        for ch in range(8):
            label = QLabel(f"CH{ch+1}: 0.00V")
            label.setStyleSheet("""
                QLabel {
                    font-size: 14px; 
                    font-weight: bold; 
                    padding: 8px; 
                    background-color: #f0f0f0; 
                    border-radius: 5px;
                    border: 1px solid #ddd;
                }
            """)
            label.setMinimumHeight(40)
            label.mouseDoubleClickEvent = lambda e, a=amp_index, c=ch: self.start_single_test(f'AMP{a+1}_CH{c+1}')
            grid_layout.addWidget(label, ch//4, ch%4)
            key = f'AMP{amp_index+1}_CH{ch+1}'
            self.amp_value_labels[key] = label
        
        layout.addLayout(grid_layout)
        
        # 波形显示
        plot_widget = pg.PlotWidget()
        plot_widget.setLabel('left', '电压', units='V')
        plot_widget.setLabel('bottom', '采样点')
        plot_widget.setTitle(f'放大器 {amp_index+1} 实时波形 (双击通道开始测试)')
        plot_widget.showGrid(x=True, y=True, alpha=0.3)
        plot_widget.setBackground('w')
        
        curves = []
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A',
                  '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        
        for ch in range(8):
            curve = plot_widget.plot(
                pen=pg.mkPen(color=colors[ch], width=2),
                name=f'CH{ch+1}'
            )
            curves.append(curve)
        
        plot_widget.addLegend()
        layout.addWidget(plot_widget, 3)
        
        tab.curves = curves
        tab.plot_widget = plot_widget
        
        tab.setLayout(layout)
        return tab
    
    def show_select_channels(self):
        """显示选择通道对话框"""
        if not self.is_running:
            QMessageBox.warning(self, "警告", "请先开始采集")
            return
        
        dialog = SelectChannelsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            channels = dialog.selected_channels
            if channels:
                self.start_batch_test(channels)
    
    def batch_test_all(self):
        """批量测试所有通道"""
        if not self.is_running:
            QMessageBox.warning(self, "警告", "请先开始采集")
            return
        
        reply = QMessageBox.question(
            self,
            "批量测试",
            "将测试所有152个通道，\n每个通道测试5秒。\n\n是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            channels = list(self.system.data_buffers.keys())
            self.start_batch_test(channels)
    
    def test_abnormal_channels(self):
        """测试异常通道"""
        if not self.is_running:
            QMessageBox.warning(self, "警告", "请先开始采集")
            return
        
        abnormal_channels = [
            key for key, status in self.system.channel_status.items()
            if status in ['abnormal', 'failed']
        ]
        
        if not abnormal_channels:
            QMessageBox.information(self, "信息", "没有异常通道需要测试")
            return
        
        reply = QMessageBox.question(
            self,
            "测试异常通道",
            f"发现 {len(abnormal_channels)} 个异常通道，\n是否开始测试？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_batch_test(abnormal_channels)
    
    def start_batch_test(self, channels):
        """开始批量测试"""
        self.batch_thread = BatchTestThread(self, channels)
        self.batch_thread.progress_updated.connect(self.on_batch_progress)
        self.batch_thread.finished.connect(self.on_batch_finished)
        self.batch_thread.start()
        
        self.btn_select_test.setEnabled(False)
        self.btn_batch_test.setEnabled(False)
        self.btn_test_abnormal.setEnabled(False)
        self.test_progress_bar.setValue(0)
    
    def on_batch_progress(self, current, total, channel_key, status):
        """批量测试进度更新"""
        progress = int(current / total * 100)
        self.test_progress_bar.setValue(progress)
        self.test_status_label.setText(f"🔬 测试中: {current}/{total} - {channel_key} - {status}")
        
        # 更新统计
        self.update_statistics()
    
    def on_batch_finished(self, results):
        """批量测试完成"""
        self.btn_select_test.setEnabled(True)
        self.btn_batch_test.setEnabled(True)
        self.btn_test_abnormal.setEnabled(True)
        self.test_progress_bar.setValue(100)
        
        passed = sum(1 for r in results if r['status_code'] == 'passed')
        failed = len(results) - passed
        
        QMessageBox.information(
            self,
            "批量测试完成",
            f"测试完成！\n\n"
            f"测试通道: {len(results)}\n"
            f"✅ 通过: {passed}\n"
            f"❌ 失败: {failed}\n\n"
            f"详细结果已更新到界面"
        )
        
        self.test_status_label.setText(f"批量测试完成: {passed}/{len(results)} 通过")
        self.update_statistics()
    
    def start_single_test(self, channel_key):
        """启动单通道测试"""
        if not self.is_running:
            QMessageBox.warning(self, "警告", "请先开始采集")
            return
        
        self.test_dialog = ChannelTestDialog(self, channel_key)
        self.test_dialog.show()
        
        self.test_status_label.setText(f"🔬 测试通道: {channel_key}")
        self.test_status_label.setStyleSheet("color: blue; font-weight: bold;")
    
    def start_channel_test(self, channel_key, signal_type):
        """由测试对话框调用"""
        self.acquisition_thread.start_test(channel_key, signal_type)
        self.system.channel_status[channel_key] = 'testing'
        self.update_channel_indicator(channel_key, 'testing')
        self.update_statistics()
    
    def stop_channel_test(self):
        """由测试对话框调用"""
        if self.acquisition_thread.test_channel:
            channel_key = self.acquisition_thread.test_channel
            # 状态已经在测试对话框中更新，这里不需要重复设置
            self.update_channel_indicator(channel_key, self.system.channel_status.get(channel_key, 'normal'))
        
        self.acquisition_thread.stop_test()
        self.test_status_label.setText("测试状态: 完成")
        self.update_statistics()
    
    def update_channel_indicator(self, channel_key, status):
        """更新通道指示器颜色"""
        for i, key in enumerate(self.system.data_buffers.keys()):
            if key == channel_key and i < 152:
                if status == 'testing':
                    color = "#3498db"
                elif status in ['passed', 'normal']:
                    color = "#2ecc71"
                elif status in ['failed', 'abnormal']:
                    color = "#e74c3c"
                else:
                    color = "#95a5a6"
                
                self.channel_indicators[i].setStyleSheet(f"""
                    QLabel {{
                        background-color: {color}; 
                        border: 1px solid #333; 
                        color: white;
                        font-weight: bold;
                        border-radius: 3px;
                    }}
                """)
                break
        self.update_statistics()
    
    def update_statistics(self):
        """更新统计信息"""
        total = 152
        passed = sum(1 for s in self.system.channel_status.values() if s == 'passed')
        failed = sum(1 for s in self.system.channel_status.values() if s in ['failed', 'abnormal'])
        testing = sum(1 for s in self.system.channel_status.values() if s == 'testing')
        untested = total - passed - failed - testing
        
        self.stats_passed.setText(f"✅ 通过: {passed}")
        self.stats_failed.setText(f"❌ 失败: {failed}")
        self.stats_untested.setText(f"⚪ 未测试: {untested}")
        
        self.lbl_passed.setText(f"✅ 通过: {passed}")
        self.lbl_failed.setText(f"❌ 失败: {failed}")
        self.lbl_testing.setText(f"🔵 测试中: {testing}")
        self.lbl_untested.setText(f"⚪ 未测试: {untested}")
    
    def on_tab_changed(self, index):
        if index == 0:
            self.status_label.setText("📊 显示概览模式")
        else:
            amp_idx = index - 1
            self.status_label.setText(f"📈 显示放大器 {amp_idx+1}")
    
    def start_acquisition(self):
        if not self.is_running:
            self.is_running = True
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.acquisition_thread.start()
            self.status_label.setText("🟢 采集中...")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
    
    def stop_acquisition(self):
        self.is_running = False
        self.acquisition_thread.stop()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("⏹ 已停止")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def on_data_received(self, data):
        for key, value in data.items():
            if key in self.system.data_buffers:
                buffer = self.system.data_buffers[key]
                buffer = np.roll(buffer, -1)
                buffer[-1] = value
                self.system.data_buffers[key] = buffer
        
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:
            self.update_overview(data)
        else:
            amp_idx = current_tab - 1
            self.update_amplifier_tab(amp_idx, data)
        
        self.sample_count += 1
        progress = min(100, (self.sample_count % 1000) * 100 // 1000)
        self.progress_bar.setValue(progress)
    
    def update_overview(self, data):
        for i, key in enumerate(self.system.data_buffers.keys()):
            if i < 152:
                status = self.system.channel_status.get(key, 'normal')
                
                if status == 'testing':
                    color = "#3498db"
                elif status in ['passed', 'normal']:
                    color = "#2ecc71"
                elif status in ['failed', 'abnormal']:
                    color = "#e74c3c"
                else:
                    color = "#95a5a6"
                
                self.channel_indicators[i].setStyleSheet(f"""
                    QLabel {{
                        background-color: {color}; 
                        border: 1px solid #333; 
                        color: white;
                        font-weight: bold;
                        border-radius: 3px;
                    }}
                """)
    
    def update_amplifier_tab(self, amp_idx, data):
        for ch in range(8):
            key = f'AMP{amp_idx+1}_CH{ch+1}'
            if key in self.amp_value_labels:
                value = data.get(key, 0)
                self.amp_value_labels[key].setText(f"CH{ch+1}: {value:.3f}V")
                
                status = self.system.channel_status.get(key, 'normal')
                if status == 'testing':
                    style = """
                        QLabel {
                            font-size: 14px; 
                            font-weight: bold; 
                            padding: 8px; 
                            background-color: #3498db; 
                            border-radius: 5px;
                            border: 2px solid blue;
                            color: white;
                        }
                    """
                elif status in ['passed', 'normal']:
                    style = """
                        QLabel {
                            font-size: 14px; 
                            font-weight: bold; 
                            padding: 8px; 
                            background-color: #d4edda; 
                            border-radius: 5px;
                            border: 1px solid #28a745;
                            color: #155724;
                        }
                    """
                elif status in ['failed', 'abnormal']:
                    style = """
                        QLabel {
                            font-size: 14px; 
                            font-weight: bold; 
                            padding: 8px; 
                            background-color: #f8d7da; 
                            border-radius: 5px;
                            border: 2px solid red;
                            color: #721c24;
                        }
                    """
                else:
                    style = """
                        QLabel {
                            font-size: 14px; 
                            font-weight: bold; 
                            padding: 8px; 
                            background-color: #f0f0f0; 
                            border-radius: 5px;
                            border: 1px solid #ddd;
                        }
                    """
                self.amp_value_labels[key].setStyleSheet(style)
        
        tab = self.amp_tabs[amp_idx]
        for ch in range(8):
            key = f'AMP{amp_idx+1}_CH{ch+1}'
            buffer = self.system.data_buffers[key]
            tab.curves[ch].setData(buffer)
    
    def save_data(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "保存数据", 
            f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "CSV文件 (*.csv);;所有文件 (*)"
        )
        
        if filename:
            try:
                import pandas as pd
                df = pd.DataFrame(self.system.data_buffers)
                df.to_csv(filename, index=False)
                QMessageBox.information(self, "成功", f"✅ 数据已保存到:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"❌ 保存失败:\n{str(e)}")
    
    def closeEvent(self, event):
        if self.is_running:
            self.stop_acquisition()
        if hasattr(self, 'acquisition_thread'):
            self.acquisition_thread.wait()
        event.accept()

# ============ 主程序入口 ============
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = MultiAmplifierMonitor()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    import re
    test_threshold =  list(map(float, re.findall(r'-?\d+\.?\d*', "[-160N, 60N]")))
    print(test_threshold[0])