#!/usr/bin/python3
# -*-coding:Utf-8 -*

import logging
import sys,os, time
from PySide6.QtGui import QIcon, QScreen, QKeySequence, QShortcut
import serial,serial.tools.list_ports
import threading
import json

#interface import
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTextEdit, QLineEdit, QPushButton, QMessageBox, QWidget, QGridLayout, QTextEdit, QGroupBox, QVBoxLayout,QHBoxLayout, QComboBox, QScrollArea


__prgm__ = 'Serial Monitor'
__version__ = '1.0.0'

logging.basicConfig(filename='logs.log', level=logging.DEBUG,format='%(asctime)s: %(levelname)s: %(funcName)s: %(message)s: %(lineno)d')
user = os.getlogin()

def find_USB_device(USB_DEV_NAME=None):
    myports = [tuple(p) for p in list(serial.tools.list_ports.comports())]
    #usb_port_list = [p[0] for p in myports]
    #usb_device_list = [p[1] for p in myports]

    if USB_DEV_NAME is None:
        return myports
    else:
        usb_id = ""
        for i in range(0,len(USB_DEV_NAME)):
            if USB_DEV_NAME[i] == '(':
                usb_id = USB_DEV_NAME [i+1 : len(USB_DEV_NAME)-1]
                logging.debug(f'{user}: USB ID--> {USB_DEV_NAME} {usb_id}')
                return (usb_id)
    

#################Graphical interface########################                
class GroupClass(QGroupBox):
    def __init__(self,widget,title="Connection Configuration"):
        super().__init__(widget)
        self.widget=widget
        self.title=title
        self.sep="-"
        self.id=-1
        self.name=''
        self.portlist=find_USB_device()
        self.command_list = self.read_json()
        self.items=[p[1] for p in self.portlist if "USB Serial Device" in p[1] or "Arduino" in p[1]]#["COM1","COM2"]#It goes by name now and I tried to filter irrelevant ports
        '''it shows Arduino if the laptop has arduino drivers installed and shows USB Serial Device if not'''
        self.command = [c for c in self.command_list]
        self.serial=None
        #self.motionDict={"POSITION BASED":" Describe motion based on position","VELOCITY BASED":" Describe motion based on velocity", "LOOP":" Describe loop motion", "PINGPONG":" Describe pingpong motion", "INTERACTIF":" Describe interactive motion"}
        self.config_gui = ConfigGUI()
        self.json_window = JsonDisplayWindow()
        self.init()
        
#GUI Widgets       
    def init(self):
        self.setTitle(self.title)
        
        self.selectlbl = QLabel("Select port:")
        #label
        self.typeBox=QComboBox()
        self.typeBox.addItems(self.items)#database getMotionType()
        self.typeBox.setCurrentIndex(self.typeBox.count()-1)
        
        #btn
        button = QPushButton("Connect")
        button.clicked.connect(self.connect)
        #hbox.addWidget(button)
        
        sendBtn = QPushButton("Send")
        sendBtn.clicked.connect(self.start_send_thread)
        #hbox.addWidget(button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.widget.refresh_program)

        #show json button
        #jsonButton = QPushButton("Show Json")
        # jsonButton.clicked.connect(self.show_json_window)
        show_json_button = QPushButton("Show JSON File")
        show_json_button.clicked.connect(self.config_gui.toggle_json_display)

        #label
        self.selectlbl2 = QLabel("Select Command")

        #Qcombobox
        self.typeBox2=QComboBox()
        self.typeBox2.addItems(self.command)
        self.typeBox2.setCurrentIndex(self.typeBox.count()-1)
        
        titlelbl=  QLabel("Select Command")
        self.title = QLineEdit("")
        desclbl=QLabel("Console")
        self.desc = QTextEdit("")
            
        self.fields=QGridLayout()
        self.fields.addWidget(self.selectlbl,0,0,1,1)
        self.fields.addWidget(self.typeBox,0,1,1,1)
        self.fields.addWidget(button,0,2,1,1)
        self.fields.addWidget(refresh_button,0,2,0,2)
        self.fields.addWidget(show_json_button,3,2,3,4)
        
        self.fields.addWidget(titlelbl,1,0,1,1)
        self.fields.addWidget(self.typeBox2,1,1,1,1)
        #self.fields.addWidget(self.title,1,1,1,1)
        self.fields.addWidget(sendBtn,1,2,1,1)
        self.fields.addWidget(desclbl,2,0,1,1)
        self.fields.addWidget(self.desc,3,1,1,1)
        #self.fields.addWidget(self.add,2,2,1,1)
        #self.fields.addWidget(self.rem,3,2,1,1)
        self.setLayout(self.fields)

        secret_shortcut = QShortcut(QKeySequence('Ctrl+Shift+O'), self)
        secret_shortcut.activated.connect(self.secret_function)
 
    def read_json(self):
        try:
            with open(fr'C:\ProgramData\Arduino Control\dict.json', 'r') as f:
                data = json.load(f)
                commands = {}
                commands = data
                return commands
        except FileNotFoundError:
            logging.warning("dict file was deleted")
            QMessageBox.warning(self, "Error", "Please delete the config.json file and reopen the app again.")
         

#Connect button implementation 
    def connect(self):
        self.desc.setText("")
        self.desc.setText(">> trying to connect to port %s ..." % self.typeBox.currentText())
        if "" == self.typeBox.currentText():
            self.desc.setText(self.desc.toPlainText()+"\n>> No port selected")
            return
        try:
            logging.info(f"Connecting to port {self.typeBox.currentText()}")
            self.serial = serial.Serial(find_USB_device(self.typeBox.currentText()), 9600, timeout=1)
            answer=self.readData()
            if answer!=" ":
                self.desc.setText(self.desc.toPlainText()+"\n>> Connected!\n"+answer)
                logging.debug(f"{user}: Arduino connected--> {self.typeBox.currentText()}")
        except Exception as e:
            if self.serial.portstr != None:
                self.desc.setText(f">> {self.serial.portstr} is already connected\n")
            else: 
                self.desc.setText(">> {}\n".format(e))
                logging.error(f"{user}: Cannot connect to port {self.typeBox.currentText}--> {e}")

    def start_send_thread(self):
        if not self.serial:
            self.desc.setText(">> No connection established. Press Refresh then Connect Button")
            return
        # Start a new thread to handle the sendData function
        send_thread = threading.Thread(target=self.sendData)
        send_thread.start()

#Send button implementation          
    def sendData(self):
        try:
            self.serial.isOpen()
            self.desc.append(">> Sending Commads....\n")
            if self.read_json().get(self.typeBox2.currentText()) != "":
                counter = 0
                for command in self.read_json().get(self.typeBox2.currentText()).values():                
                    self.serial.write(command.encode())
                    time.sleep(1.5)  
                    
                    #print (self.serial.inWaiting())
                    if (counter == len(self.read_json().get(self.typeBox2.currentText()))-1) and self.serial.inWaiting()>0:
                        self.serial.reset_input_buffer()
                        #print (self.serial.inWaiting())
                        self.desc.append(f"Received from Arduino >> {self.typeBox2.currentText()}\n")
                        self.desc.append("#######################\n")
                    elif (counter == len(self.read_json().get(self.typeBox2.currentText()))-1) and self.serial.inWaiting() == 0:
                        self.desc.append(f"Nothing Recived from Arduino >>\n")
                        self.desc.append("#######################\n")
                    
                    #Logging the commands that are sent
                    if counter == 0:
                        logging.info(f"{user}: key command--> {self.typeBox2.currentText()}")    
                    logging.info(f"{user}: sub command: {list(self.read_json().get(self.typeBox2.currentText()).values())[counter]}")
                    counter += 1

        except AttributeError:
            self.desc.append("Press Refresh then Connect Button")
        except Exception as e:
            self.desc.setText(f"{e}")
        
            
#Reading any output from the arduino                  
    def readData(self):
        answer=""
        time.sleep(0.5)
        while  self.serial.inWaiting()>0:
            answer += "\n"+str(self.serial.readline()).replace("\\r","").replace("\\n","").replace("'","").replace("b","")
        return answer
    
    def secret_function(self):
        self.desc.setText(f"Made by meujoy")

#GUI main window           
class SerialInterface(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.width=650
        self.height=350
        
        self.resize(self.width, self.height)
        self.setWindowIcon(QIcon('logo.png'))
        self.setWindowTitle(__prgm__)
        
        #center window on screen
        qr = self.frameGeometry()
        cp = QScreen().availableGeometry().center()
        qr.moveCenter(cp)
        
        
        #init layout
        centralwidget = QWidget(self)
        centralLayout=QHBoxLayout(centralwidget)
        self.setCentralWidget(centralwidget)
        
        #add connect group
        self.connectgrp=GroupClass(self)
        centralLayout.addWidget(self.connectgrp)
        
    def refresh_program(self):
        logging.info("Refresh button pressed")
        self.connectgrp.serial = None
        self.connectgrp.desc.clear()
        self.connectgrp.typeBox.clear()
        self.connectgrp.typeBox.addItems([p[1] for p in find_USB_device() if "USB Serial Device" in p[1] or "Arduino" in p[1]])
        self.connectgrp.typeBox.setCurrentIndex(self.connectgrp.typeBox.count() - 1)
        self.connectgrp.typeBox2.setCurrentIndex(self.connectgrp.typeBox2.count() - 1)
        self.connectgrp.desc.setText(">> Interface refreshed.")
        #self.connectgrp.connect() #this reset all arduino relays as it disconnects and connect again    

        
class ConfigGUI(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.width = 650
        self.height = 350

        self.setWindowTitle("Commands Setup")

        self.available_values = ["close Relay00", "open Relay00", "close Relay01", "open Relay01",
                                 "close Relay02", "open Relay02", "close Relay03", "open Relay03",
                                 "close Relay04", "open Relay04", "close Relay05", "open Relay05",
                                 "close Relay06", "open Relay06", "close Relay07", "open Relay07",
                                 "close Relay08", "open Relay08", "close Relay09", "open Relay09",
                                 "close Relay010", "open Relay010"]
        self.textbox_text = []
        self.setup_ui()

    def setup_ui(self):
        self.resize(self.width, self.height)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Create the main layout
        main_layout = QVBoxLayout(central_widget)

        # Create and add QLabel and QLineEdit at the top
        label = QLabel("The text entered below will be the name that appears on the GUI:", self)
        self.line_edit = QLineEdit(self)
        main_layout.addWidget(label)
        main_layout.addWidget(self.line_edit)

        # Create a scroll area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)

        # Add the QLabel at the top of the scroll area
        self.top_label = QLabel("Relay00-->Pin2, Relay01-->Pin3, Relay02-->Pin4, Relay03-->Pin5, Relay04-->Pin6,Relay05-->Pin7, Relay06-->Pin8", self)
        self.scroll_layout.addWidget(self.top_label)

        # Add scroll area to the main layout
        main_layout.addWidget(self.scroll_area)

        # Create a horizontal layout for buttons
        button_layout = QHBoxLayout()

        # Create the "Add QComboBox" button
        self.button_add = QPushButton("Add Command", self)
        self.button_add.clicked.connect(self.add_combo_box)
        button_layout.addWidget(self.button_add)

        # Create the "Next" button
        self.another_button = QPushButton("Next Block", self)
        self.another_button.clicked.connect(self.next_action)
        button_layout.addWidget(self.another_button)

        # Create the "Show JSON" button
        self.show_json_button = QPushButton("Show JSON File", self)
        self.show_json_button.clicked.connect(self.toggle_json_display)
        button_layout.addWidget(self.show_json_button)

        # Create the "Done" button
        self.done_button = QPushButton("Done", self)
        self.done_button.clicked.connect(self.done_action)
        self.done_button.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.done_button)

        # Create the "Reset" button
        self.reset_button = QPushButton("Reset JSON", self)
        self.reset_button.clicked.connect(self.reset_action)
        self.reset_button.setStyleSheet("background-color: red; color: white;")
        button_layout.addWidget(self.reset_button)

        # Add button layout to the main layout
        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)

        self.row_count = 0
        self.combo_boxes = []
        self.labels = []
        self.add_combo_box()

        # Initialize JSON display window as None
        self.json_window = None

    def add_combo_box(self):
        if not self.get_available_values():
            self.button_add.setEnabled(False)
            return

        label = QLabel(f"command{self.row_count + 1}", self)
        combo_box = QComboBox(self)
        combo_box.addItems(self.get_available_values())
        combo_box.currentIndexChanged.connect(self.update_combo_boxes)

        # Create a horizontal layout for the new row
        row_layout = QHBoxLayout()
        row_layout.addWidget(label)
        row_layout.addWidget(combo_box)

        # Add the new row layout to the scroll layout
        self.scroll_layout.addLayout(row_layout)

        self.labels.append(label)
        self.combo_boxes.append(combo_box)
        self.row_count += 1

    def get_available_values(self):
        selected_values = [combo_box.currentText() for combo_box in self.combo_boxes if combo_box.currentIndex() != -1]
        return [value for value in self.available_values if value not in selected_values]

    def update_combo_boxes(self):
        self.button_add.setEnabled(bool(self.get_available_values()))

        for combo_box in self.combo_boxes:
            current_value = combo_box.currentText()
            combo_box.blockSignals(True)
            combo_box.clear()
            combo_box.addItems(self.get_available_values())
            if current_value in [combo_box.itemText(i) for i in range(combo_box.count())]:
                combo_box.setCurrentText(current_value)
            combo_box.blockSignals(False)

    def generate_json(self):
        input_text = self.line_edit.text()

        if  input_text not in self.textbox_text:
            self.textbox_text.append(input_text)
        else:
            QMessageBox.warning(self, "Input Error", "The key names in the json cannot be duplicated.")
            return 0

        if not input_text:
            QMessageBox.warning(self, "Input Error", "Please enter text in the textbox above.")
            return

        data = {}
        try:
            with open(fr'C:\ProgramData\Arduino Control\dict.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            pass

        if input_text not in data:
            data[input_text] = {}

        for combo_box, label in zip(self.combo_boxes, self.labels):
            label_text = label.text()
            chosen_option = combo_box.currentText()
            data[input_text][label_text] = chosen_option

        with open(fr'C:\ProgramData\Arduino Control\dict.json', 'w') as f:
            json.dump(data, f, indent=4)
            logging.info(f"{user}: Added entries to JSON file 'dict.json' successfully -- contents--> {data}.")
        self.clear_inputs()

    def clear_inputs(self):
        self.line_edit.clear()
        for combo_box, label in zip(self.combo_boxes, self.labels):
            self.scroll_layout.removeWidget(label)
            self.scroll_layout.removeWidget(combo_box)
            label.deleteLater()
            combo_box.deleteLater()
        self.labels.clear()
        self.combo_boxes.clear()
        self.row_count = 0
        self.add_combo_box()

    def next_action(self):
        self.generate_json()

    def done_action(self):
        flag = self.generate_json()
        self.done_button.setStyleSheet("background-color: green; color: white;")
        if flag != 0:
            self.show_main_window()
            logging.info(f"{user}: JSON file 'dict.json' created successfully")
        else:
            return

    def reset_action(self):
        if os.path.exists(fr'C:\ProgramData\Arduino Control\dict.json'):
            os.remove(fr'C:\ProgramData\Arduino Control\dict.json')
            logging.info("{user}: JSON file 'dict.json' deleted successfully.")

        self.clear_inputs()
        QMessageBox.information(self, "Progress Reset", "Progress has been reset.")
        self.done_button.setStyleSheet("background-color: #4CAF50; color: white;")

    def toggle_json_display(self):
        if not self.json_window or not self.json_window.isVisible():
            self.show_json_window()
        else:
            self.close_json_window()

    def show_json_window(self):
        self.json_window = JsonDisplayWindow()
        self.json_window.show()

    def close_json_window(self):
        if self.json_window:
            self.json_window.close()
    
    def show_main_window(self):
        w = SerialInterface()
        w.show()
        config_window.close()

class JsonDisplayWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JSON Display")
        self.setGeometry(100, 100, 400, 300)

        self.text_edit = QTextEdit(self)
        self.setCentralWidget(self.text_edit)

        self.load_json()

    def load_json(self):
        try:
            with open(fr'C:\ProgramData\Arduino Control\dict.json', 'r') as f:
                data = json.load(f)
                json_text = json.dumps(data, indent=4)
                self.text_edit.setPlainText(json_text)
        except FileNotFoundError:
            self.text_edit.setPlainText("No JSON file found.")

class WarningWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ERROR")
        self.resize(200, 200)
        self.center()

    def center(self):
        
        # Get the screen geometry
        screen_geometry = self.screen().geometry()
        # Get the size of the window
        window_geometry = self.frameGeometry()
        # Calculate the position for the window to be centered
        x = (screen_geometry.width() - window_geometry.width()) // 2
        y = (screen_geometry.height() - window_geometry.height()) // 2
        self.move(x, y)


if __name__ == "__main__":
    logging.info("=================== Arduino Control 1.0.0 ==========================")
    logging.info(f"User using the APP--> {user}")
    
    try:
        logging.info("Creating Commands File")
        os.makedirs('C:\ProgramData\Arduino Control')
        logging.info("File created successfully")
    except OSError as e:
        if hasattr(e,'winerror'):
            if e.winerror == 183:      
                logging.info("File already exists")
    except Exception as e:
        logging.debug(e)
    
    if os.path.isfile("config.json"):
        
        with open("config.json", "r") as f:
            json_object = json.load(f)
        
        try:
            if json_object['State'] == 1:
                app = QApplication(sys.argv)
                main_window = SerialInterface()
                main_window.show()
                sys.exit(app.exec_())
        except Exception as e:
            print (e)
            logging.error(f"{user}: Config.json contents were altered -- Changed to --> {json_object}")
            app = QApplication(sys.argv)
            ww = WarningWindow()
            QMessageBox.warning(ww,"Error","Please Don't change the contents of the json file, just delete the file and start the program again")
            
    else:
        with open("config.json", "w") as f:
            state = {}
            state['State'] = 1
            json.dump(state, f)
        
        if os.path.exists(fr'C:\ProgramData\Arduino Control\dict.json'):
            os.remove(fr'C:\ProgramData\Arduino Control\dict.json')
        
        app = QApplication(sys.argv)
        config_window = ConfigGUI()
        config_window.show()
        sys.exit(app.exec_())