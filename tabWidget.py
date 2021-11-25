import pandas as pd
import re
import psycopg2
import qdarkstyle
from PyQt5 import QtWidgets, uic, QtGui
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QAbstractItemView, QApplication, QDialog, QGridLayout, \
    QDesktopWidget, QMessageBox
from PyQt5.QtCore import Qt, QSortFilterProxyModel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('./qtdesigner/tabWidget.ui', self)
        self.setWindowIcon(QtGui.QIcon('./media/uf.png'))

        #  TAB 1: Database management
        #  serverField
        self.serverField = self.findChild(QtWidgets.QLineEdit, 'serverField')

        #  databaseField
        self.databaseField = self.findChild(QtWidgets.QLineEdit, 'databaseField')

        #  usernameField
        self.usernameField = self.findChild(QtWidgets.QLineEdit, 'usernameField')

        #  passwordField
        self.passwordField = self.findChild(QtWidgets.QLineEdit, 'passwordField')
        self.passwordField.setEchoMode(QtWidgets.QLineEdit.Password)

        #  loginButton
        self.loginButton = self.findChild(QtWidgets.QPushButton, 'loginButton')
        self.loginButton.clicked.connect(self.login)

        #  loginLabel
        self.loginLabel = self.findChild(QtWidgets.QLabel, 'loginLabel')

        #  uploadButton
        self.uploadButton = self.findChild(QtWidgets.QPushButton, 'uploadButton')
        self.uploadButton.clicked.connect(self.upload)

        #  progressLabel
        self.progressLabel = self.findChild(QtWidgets.QLabel, 'progressLabel')

        #  TAB 2: Get information from database
        #  queryField
        self.queryField = self.findChild(QtWidgets.QLineEdit, 'queryField')

        #  querySearch
        self.querySearch = self.findChild(QtWidgets.QLabel, 'querySearch')

        #  queryList
        self.queryList = self.findChild(QtWidgets.QListView, 'queryList')
        self.queryList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        model = QtGui.QStandardItemModel()
        self.queryList.setModel(model)
        self.query_dict = pd.read_csv('./text/queries.txt', sep="|", header=None, index_col=0, squeeze=True).to_dict()
        for query in self.query_dict.keys():
            item = QtGui.QStandardItem(query)
            model.appendRow(item)
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        filter_proxy_model.setFilterKeyColumn(0)
        self.queryField.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.queryList.setModel(filter_proxy_model)

        #  querySelect
        self.querySelect = self.findChild(QtWidgets.QPushButton, 'querySelect')
        self.querySelect.clicked.connect(self.format_params_dialog)

        #  TAB 3: Advanced database search
        #  advField
        self.advField = self.findChild(QtWidgets.QLineEdit, 'advField')

        #  advEnter
        self.advEnter = self.findChild(QtWidgets.QPushButton, 'advEnter')
        self.advEnter.clicked.connect(self.advanced_query)

        #  advBrowser
        self.advBrowser = self.findChild(QtWidgets.QTextBrowser, 'advBrowser')

        #  TAB 4: How to use
        #  helpCombo
        self.helpCombo = self.findChild(QtWidgets.QComboBox, 'helpCombo')
        self.helpCombo.activated.connect(self.change_text)

        #  helpBrowser
        self.helpBrowser = self.findChild(QtWidgets.QTextBrowser, 'helpBrowser')
        self.helpBrowser.setAcceptRichText(True)
        #  function for changing display text via combobox
        text = open('./text/help/introToTheProgram.txt').read()
        self.helpBrowser.setText(text)
        self.helpBrowser.setFont(QFont('Times', 12))
    #   ---------------------------------------------------------------

    def credentials(self):
        param_dic = {
            'host': self.serverField.text(),
            'database': self.databaseField.text(),
            'user': self.usernameField.text(),
            'password': self.passwordField.text()
        }
        return param_dic

    @staticmethod
    def connect(params_dic):
        conn = None
        try:
            conn = psycopg2.connect(**params_dic)
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)
        return conn

    def login(self):
        authenticate = self.connect(self.credentials())
        if authenticate:
            self.loginLabel.setStyleSheet('background-color: #42ba96')
            self.loginLabel.setText('LOGIN SUCCESSFUL.')
            self.uploadButton.setEnabled(True)
            self.querySelect.setEnabled(True)
            self.advEnter.setEnabled(True)
        else:
            self.loginLabel.setStyleSheet('background-color: #df4759')
            self.loginLabel.setText('LOGIN FAILED. CHECK YOUR CREDENTIALS.')
            self.uploadButton.setEnabled(False)
            self.querySelect.setEnabled(False)
            self.advEnter.setEnabled(False)
        return authenticate

    #   ---------------------------------------------------------------

    @staticmethod
    def table_exists(con, table_name):
        cur = con.cursor()
        cur.execute('''
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = '{0}'
            '''.format(table_name.replace('\'', '\'\'')))
        if cur.fetchone()[0] == 1:
            cur.close()
            return True
        cur.close()
        return False

    def upload(self):
        # Get Excel file
        path = QFileDialog.getOpenFileName(None, 'Open a file', '', 'Excel files (*.xlsx)',
                                           options=QFileDialog.DontUseNativeDialog)
        if path != ('', ''):
            excel = path[0]
        else:
            return
        try:
            df = pd.read_excel(excel)
            semester = df.columns[0].split(' ')[-2].upper()
            year = int(df.columns[0].split(' ')[-1])
            df = pd.read_excel(excel, dtype=object, skiprows=8)
            # Format column names to match database column names
            df.columns = df.columns.str.lower()
            df.columns = df.columns.str.replace(' ', '_')
            df.columns = df.columns.str.replace('/', '_')
            df.rename(columns={'day_s': 'days', 'min_-_max_cred': 'min_max_cred'}, inplace=True)
            table_name = 'courses'
            # Don't use the | key in the Excel sheet, as it will corrupt the data when it goes to the database.
            con = self.connect(self.credentials())
            cur = con.cursor()
            # Create table if it doesn't exist
            if not self.table_exists(con, table_name):
                query = 'CREATE TABLE ' + table_name + ' (session_code INT, \
                session_begin_date DATE, session_end_date DATE, drop_add_end_date DATE, grading_end_date DATE, \
                course TEXT, gord_rule TEXT, gen_ed TEXT, hons_list TEXT, sect TEXT, class_nbr INT , assoc_class INT, \
                min_max_cred TEXT, days TEXT, time TEXT, meeting_pattern TEXT, facility TEXT, join_num TEXT, site TEXT, \
                county TEXT, spec TEXT, book TEXT, soc TEXT, exam TEXT, course_title TEXT, instructor TEXT, \
                instructor_emails TEXT, enr_cap INT, room_cap INT, enrolled INT, multi_meet_cap INT, \
                sched_codes TEXT, class_status TEXT, semester TEXT, year INT);'
                cur.execute(query)
            # Delete outdated entries
            sep = '|'
            replace_query = 'DELETE FROM ' + table_name + ' WHERE semester = \'' + semester + '\' AND year = ' + \
                            str(year) + ';'
            cur.execute(replace_query)
            df['semester'] = semester
            df['year'] = year
            df.columns = df.columns.str.strip()
            # Format 'instructor' column (remove comma and flip names)
            df['instructor'] = df['instructor'].replace(['-'], 'NONE,FOUND')
            df['instructor'].fillna('FOUND,NONE', inplace=True)
            df["instructor"] = [" ".join(x.split(",")[::-1]) for x in df["instructor"]]
            # Remove NaN values and convert to uppercase
            df.fillna(0, inplace=True)
            df = df.applymap(lambda x: x.upper() if type(x) == str else x)
            # Load dataframe to CSV file so it can be copied to database
            df.to_csv('./text/out.txt', sep=sep, index=False, header=False)
            f = open('./text/out.txt', 'r')
            cur.copy_from(f, table_name, sep=sep)
            con.commit()
            f.close()
            con.close()
            self.progressLabel.setText('YOU UPLOADED: ' + excel + ' FOR ' +
                                       semester + ' ' + str(year))
            print(df.dtypes)
        except Exception:
            QMessageBox.critical(self, "Critical error", "This Excel file is not formatted properly. Please"
                                                         " select a new file or review this one and try again.")

    #  ---------------------------------------------------------------

    def advanced_query(self):
        con = self.connect(self.credentials())
        cur = con.cursor()
        try:
            cur.execute(self.advField.text())
        except (Exception, psycopg2.DatabaseError):
            QMessageBox.warning(self, "Attention", "Your query could not be processed. It most likely has a "
                                                   "syntax error.")
            return
        results = cur.fetchall()
        self.advBrowser.setText('')
        for x in results:
            self.advBrowser.append(str(x).replace('\'', '').strip('()'))
        con.close()

    def get_queries(self):
        if self.queryList.selectedIndexes():
            nl_query = self.queryList.selectedIndexes()[0].data()
            sql_query = self.query_dict[nl_query]
            return nl_query, sql_query
        else:
            pass

    def get_params(self):
        nl_query = self.get_queries()[0]
        sql_query = self.get_queries()[1]
        nl_regex = r'\<([A-Za-z0-9_]+)\>'
        sql_regex = r'{[A-Za-z0-9_]+}'
        nl_params = re.findall(nl_regex, nl_query)
        sql_params = re.findall(sql_regex, sql_query)
        return nl_params, sql_params

    def format_params_dialog(self):
        if self.get_queries():
            self.params_dialog = ParamsDialog()
            self.params_dialog.nl_params = self.get_params()[0]
            self.params_dialog.nl_query = self.get_queries()[0]
            self.params_dialog.sql_params = self.get_params()[1]
            self.params_dialog.sql_query = self.get_queries()[1]
            int_columns = ['session_code', 'class_nbr', 'assoc_class', 'enr_cap', 'room_cap', 'enrolled',
                           'multi_meet_cap', 'year']
            date_columns = ['session_begin_date', 'session_end_date', 'drop_add_date', 'grading_end_date']
            for item in self.params_dialog.nl_params:
                self.params_dialog.grid_layout.addWidget(QtWidgets.QLabel(item.upper()))
                param_line_edit = QtWidgets.QLineEdit()
                param_line_edit.setObjectName(item)
                if param_line_edit.objectName() in int_columns:
                    param_line_edit.setPlaceholderText("Integer field")
                elif param_line_edit.objectName() in date_columns:
                    param_line_edit.setPlaceholderText("Date field")
                else:
                    param_line_edit.setPlaceholderText("String field")
                self.params_dialog.grid_layout.addWidget(param_line_edit)
            self.params_dialog.display()
        else:
            QMessageBox.warning(self, "Attention", "Please select a question from the list.")

    #   ---------------------------------------------------------------

    def get_text(self, index, path):
        if self.helpCombo.currentIndex() == index:
            text = open(path).read()
            self.helpBrowser.setText(text)

    def change_text(self):
        self.get_text(0, './text/help/introToTheProgram.txt')
        self.get_text(1, './text/help/databaseManagement.txt')
        self.get_text(2, './text/help/getInformationFromDatabase.txt')
        self.get_text(3, './text/help/advancedDatabaseSearch.txt')
        self.get_text(4, './text/help/questionsYouMayHave.txt')
        self.get_text(5, './text/help/formatForExcelFiles.txt')
        self.get_text(6, './text/help/databaseSchema.txt')
        self.get_text(7, './text/help/addingQueries.txt')


class ParamsDialog(QDialog):

    def __init__(self):
        super().__init__()
        self.setStyleSheet("QTextBrowser{font-size: 12pt;}"
                           "QLineEdit{font-size: 12pt;}"
                           "QPushButton{font-size: 12pt;}"
                           "QLabel{font-size: 12pt;}")
        self.setWindowIcon(QtGui.QIcon('./media/uf.png'))
        self.grid_layout = QGridLayout()
        self.setWindowTitle('Enter parameters')
        # Initialize enter button
        self.sendParamsButton = QtWidgets.QPushButton("Enter")
        self.sendParamsButton.setObjectName("sendParamsButton")
        self.grid_layout.addWidget(self.sendParamsButton)
        self.sendParamsButton.clicked.connect(self.send_query)
        # -----------------------------------------------------------
        self.answerBrowser = QtWidgets.QTextBrowser()
        self.answerBrowser.setObjectName("answerBrowser")
        self.grid_layout.addWidget(self.answerBrowser)
        self.setLayout(self.grid_layout)
        self.init_ui()

    def init_ui(self):
        self.setGeometry(10, 10, 500, 300)
        self.center()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def display(self):
        self.show()

    def send_query(self):
        string_columns = ['course', 'gord_rule', 'gen_ed', 'hons_list', 'sect', 'min_max_cred', 'days', 'time',
                          'meeting_pattern', 'facility',
                          'join_num', 'site', 'county', 'spec', 'book', 'soc', 'exam', 'course_title', 'instructor',
                          'instructor_emails',
                          'sched_codes', 'class_status', 'semester']
        param_list = []
        for param in self.nl_params:
            field = self.findChild(QtWidgets.QLineEdit, param)
            field_text = field.text().upper()
            if field.objectName() in string_columns:
                print(field.objectName())
                format_params = ''
                if ',' in field_text:
                    field_text = field_text.split(',')
                    for x in field_text:
                        x = x.strip()
                        x = '\'' + x + '\','
                        format_params += x
                    format_params = format_params.rstrip(',')
                    param_list.append(format_params)
                else:
                    field_text = field_text.strip()
                    param_list.append('\'' + field_text + '\'')
            else:
                param_list.append(field_text)
        final_sql_query = self.sql_query.format(*param_list)
        print(final_sql_query)
        try:
            con = tabWindow.connect(tabWindow.credentials())
            cur = con.cursor()
            cur.execute(final_sql_query)
            results = cur.fetchall()
            self.answerBrowser.setText('')
            for x in results:
                self.answerBrowser.append(str(x).replace('\'', '').strip('()'))
            con.commit()
            con.close()
        except (Exception, psycopg2.DatabaseError):
            QMessageBox.warning(self, "Attention", "You have likely entered a parameter in an incorrect fashion. "
                                                   "Please check that you did not include letters in a YEAR "
                                                   "field, for example.")


if __name__ == '__main__':
    app = QApplication([])
    tabWindow = MainWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    tabWindow.showMaximized()
    app.exec_()
