import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QTableView, 
                            QVBoxLayout, QPushButton, QHeaderView, QDialog, QFormLayout, 
                            QLineEdit, QComboBox, QMessageBox, QDialogButtonBox, QDateEdit, QLabel)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, QDate, QFile, QTextStream

class DatabaseManager:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
    
    def get_table_data(self, table_name):
        self.cursor.execute(f"SELECT * FROM {table_name}")
        return self.cursor.fetchall()
    
    def get_table_columns(self, table_name):
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return [column[1] for column in self.cursor.fetchall()]
    
    def insert_record(self, table_name, data):
        columns = self.get_table_columns(table_name)[1:]  # 排除 ID 列
        placeholders = ', '.join(['?' for _ in columns])
        query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        self.cursor.execute(query, data)
        self.conn.commit()
        return self.cursor.lastrowid
    
    def update_record(self, table_name, record_id, data):
        columns = self.get_table_columns(table_name)[1:]  # 排除 ID 列
        set_clause = ', '.join([f"{col} = ?" for col in columns])
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        self.cursor.execute(query, (*data, record_id))
        self.conn.commit()
    
    def delete_record(self, table_name, record_id):
        query = f"DELETE FROM {table_name} WHERE id = ?"
        self.cursor.execute(query, (record_id,))
        self.conn.commit()
    
    def get_categories(self):
        self.cursor.execute("SELECT id, name FROM categories")
        return self.cursor.fetchall()
    
    def get_users(self):
        self.cursor.execute("SELECT id, username FROM users")
        return self.cursor.fetchall()
    
    def get_projects(self):
        self.cursor.execute("SELECT id, name FROM projects")
        return self.cursor.fetchall()
    
    def get_category_name(self, category_id):
        self.cursor.execute("SELECT name FROM categories WHERE id = ?", (category_id,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def get_user_name(self, user_id):
        self.cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def get_project_name(self, project_id):
        self.cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
        result = self.cursor.fetchone()
        return result[0] if result else "Unknown"

class RecordDialog(QDialog):
    def __init__(self, table_name, columns, data=None, db_manager=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{'Edit' if data else 'Add'} {table_name.capitalize()}")
        self.setMinimumWidth(500)
        self.table_name = table_name
        self.columns = columns
        self.data = data
        self.db_manager = db_manager
        
        layout = QFormLayout()
        layout.setLabelAlignment(Qt.AlignRight)
        self.inputs = {}
        
        # 跳过 ID 列
        for i, col in enumerate(columns[1:]):
            if col == "created_at" or col == "updated_at":
                continue
                
            if col.endswith("_id") or col == "category_id" or col == "assignee_id" or col == "project_id":
                combo = QComboBox()
                combo.setEditable(False)
                
                # 添加空选项
                combo.addItem("-- Select --", None)
                
                # 根据列名加载相关数据
                if col == "category_id":
                    categories = db_manager.get_categories()
                    for cat_id, name in categories:
                        combo.addItem(name, cat_id)
                elif col == "assignee_id":
                    users = db_manager.get_users()
                    for user_id, username in users:
                        combo.addItem(username, user_id)
                elif col == "project_id":
                    projects = db_manager.get_projects()
                    for project_id, name in projects:
                        combo.addItem(name, project_id)
                    
                self.inputs[col] = combo
                layout.addRow(QLabel(col.replace("_", " ").title() + ":"), combo)
                
            elif col in ["status", "priority", "severity", "type", "role"]:
                combo = QComboBox()
                combo.setEditable(False)
                
                # 根据列名添加选项
                if col == "status":
                    combo.addItems(["Planning", "In Progress", "Completed", "On Hold"])
                elif col == "priority":
                    combo.addItems(["Low", "Medium", "High", "Critical"])
                elif col == "severity":
                    combo.addItems(["Minor", "Normal", "Major", "Critical"])
                elif col == "type":
                    combo.addItems(["Task", "Bug", "Feature", "Improvement"])
                elif col == "role":
                    combo.addItems(["admin", "employee", "Manager", "Guest"])
                    
                self.inputs[col] = combo
                layout.addRow(QLabel(col.replace("_", " ").title() + ":"), combo)
                
            elif col in ["start_date", "end_date", "due_date"]:
                date_edit = QDateEdit()
                date_edit.setCalendarPopup(True)
                date_edit.setDate(QDate.currentDate())
                self.inputs[col] = date_edit
                layout.addRow(QLabel(col.replace("_", " ").title() + ":"), date_edit)
                
            elif col == "is_active":
                combo = QComboBox()
                combo.addItem("Active", 1)
                combo.addItem("Inactive", 0)
                self.inputs[col] = combo
                layout.addRow(QLabel("Status:"), combo)
                
            else:
                line_edit = QLineEdit()
                self.inputs[col] = line_edit
                layout.addRow(QLabel(col.replace("_", " ").title() + ":"), line_edit)
        
        # 设置现有数据
        if data:
            self.set_data(data)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(buttons, alignment=Qt.AlignRight)
        self.setLayout(main_layout)
    
    def set_data(self, data):
        for col, widget in self.inputs.items():
            if col not in self.columns:
                continue
                
            idx = self.columns.index(col)
            value = data[idx]
            
            if isinstance(widget, QComboBox):
                # 查找匹配的索引
                if col.endswith("_id") or col == "is_active":
                    for i in range(widget.count()):
                        if widget.itemData(i) == value:
                            widget.setCurrentIndex(i)
                            break
                else:
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)
            elif isinstance(widget, QDateEdit) and value:
                try:
                    date = QDate.fromString(value, "yyyy-MM-dd")
                    if date.isValid():
                        widget.setDate(date)
                except:
                    pass
            elif isinstance(widget, QLineEdit):
                widget.setText(str(value) if value else "")
    
    def get_data(self):
        data = []
        for col in self.columns[1:]:  # 跳过 ID 列
            if col in ["created_at", "updated_at"]:
                continue
                
            widget = self.inputs.get(col)
            if not widget:
                data.append(None)
                continue
                
            if isinstance(widget, QComboBox):
                if col.endswith("_id") or col == "is_active":
                    data.append(widget.currentData())
                else:
                    data.append(widget.currentText())
            elif isinstance(widget, QDateEdit):
                data.append(widget.date().toString("yyyy-MM-dd"))
            else:
                data.append(widget.text())
        return data

class TableTab(QWidget):
    def __init__(self, table_name, db_manager):
        super().__init__()
        self.table_name = table_name
        self.db_manager = db_manager
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        title = QLabel(f"{self.table_name.capitalize()} Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e40af;")
        main_layout.addWidget(title)
        
        # 按钮布局
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        self.add_btn = QPushButton(f"Add New {self.table_name.capitalize()}")
        self.edit_btn = QPushButton(f"Edit Selected {self.table_name.capitalize()}")
        self.delete_btn = QPushButton(f"Delete Selected {self.table_name.capitalize()}")
        self.refresh_btn = QPushButton("Refresh Data")
        
        self.add_btn.setMinimumHeight(40)
        self.edit_btn.setMinimumHeight(40)
        self.delete_btn.setMinimumHeight(40)
        self.refresh_btn.setMinimumHeight(40)
        
        self.add_btn.clicked.connect(self.add_record)
        self.edit_btn.clicked.connect(self.edit_record)
        self.delete_btn.clicked.connect(self.delete_record)
        self.refresh_btn.clicked.connect(self.load_data)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        
        # 表格视图
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.setSortingEnabled(True)
        self.model = QStandardItemModel()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_view.verticalHeader().setDefaultSectionSize(35)
        
        # 主布局
        content_layout = QVBoxLayout()
        content_layout.addWidget(self.table_view, 3)
        content_layout.addLayout(btn_layout, 1)
        
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
    
    def load_data(self):
        # 获取列名
        columns = self.db_manager.get_table_columns(self.table_name)
        
        # 设置表头
        self.model.setHorizontalHeaderLabels([col.replace("_", " ").title() for col in columns])
        
        # 获取数据
        data = self.db_manager.get_table_data(self.table_name)
        
        # 清除旧数据
        self.model.setRowCount(0)
        
        # 添加新数据
        for row_idx, row_data in enumerate(data):
            self.model.insertRow(row_idx)
            for col_idx, col_data in enumerate(row_data):
                display_value = self.get_display_value(columns[col_idx], col_data)
                item = QStandardItem(display_value)
                item.setData(row_data[0], Qt.UserRole)  # 存储 ID
                self.model.setItem(row_idx, col_idx, item)
    
    def get_display_value(self, column_name, value):
        """将外键转换为可读的名称"""
        if value is None:
            return ""
            
        if column_name == "category_id":
            return self.db_manager.get_category_name(value)
        elif column_name == "assignee_id":
            return self.db_manager.get_user_name(value)
        elif column_name == "project_id":
            return self.db_manager.get_project_name(value)
        elif column_name == "is_active":
            return "Active" if value else "Inactive"
        return str(value)
    
    def get_selected_id(self):
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return None
        return self.model.item(selected[0].row(), 0).data(Qt.UserRole)
    
    def add_record(self):
        columns = self.db_manager.get_table_columns(self.table_name)
        dialog = RecordDialog(self.table_name, columns, db_manager=self.db_manager, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_id = self.db_manager.insert_record(self.table_name, dialog.get_data())
            self.load_data()
            
            # 滚动到新添加的记录
            for row in range(self.model.rowCount()):
                if self.model.item(row, 0).data(Qt.UserRole) == new_id:
                    self.table_view.selectRow(row)
                    self.table_view.scrollTo(self.model.index(row, 0))
                    break
    
    def edit_record(self):
        record_id = self.get_selected_id()
        if not record_id:
            QMessageBox.warning(self, "Selection Required", "Please select a record to edit.")
            return
            
        columns = self.db_manager.get_table_columns(self.table_name)
        data = next((row for row in self.db_manager.get_table_data(self.table_name) if row[0] == record_id), None)
        
        if data:
            dialog = RecordDialog(self.table_name, columns, data, self.db_manager, self)
            if dialog.exec_() == QDialog.Accepted:
                self.db_manager.update_record(self.table_name, record_id, dialog.get_data())
                self.load_data()
    
    def delete_record(self):
        record_id = self.get_selected_id()
        if not record_id:
            QMessageBox.warning(self, "Selection Required", "Please select a record to delete.")
            return
            
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete this {self.table_name}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_record(self.table_name, record_id)
            self.load_data()

class DatabaseManagerApp(QMainWindow):
    def __init__(self, db_path):
        super().__init__()
        self.setWindowTitle("Task Manager Database")
        self.setGeometry(100, 100, 1200, 700)
        
        self.db_manager = DatabaseManager(db_path)
        
        # 创建主控件
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 标题
        title = QLabel("Database Management System")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e40af;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # 用户表选项卡
        self.user_tab = TableTab("users", self.db_manager)
        self.tab_widget.addTab(self.user_tab, "Users")
        
        # 类别表选项卡
        self.category_tab = TableTab("categories", self.db_manager)
        self.tab_widget.addTab(self.category_tab, "Categories")
        
        # 项目表选项卡
        self.project_tab = TableTab("projects", self.db_manager)
        self.tab_widget.addTab(self.project_tab, "Projects")
        
        main_layout.addWidget(self.tab_widget)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # 状态栏
        self.statusBar().showMessage("Ready")

def load_stylesheet():
    """加载QSS样式表"""
    try:
        style_file = QFile("static\css\syle.qss")
        if style_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(style_file)
            return stream.readAll()
    except:
        pass
    return ""

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 应用样式表
    stylesheet = load_stylesheet()
    if stylesheet:
        app.setStyleSheet(stylesheet)
    
    db_path = "databases/taskmanager.db"
    window = DatabaseManagerApp(db_path)
    window.show()
    sys.exit(app.exec_())