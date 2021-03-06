import RLPy
from PySide2 import QtWidgets
from PySide2.QtCore import Qt
from PySide2.shiboken2 import wrapInstance

#create main dialog
layer_manger_dlg = None

class LayerManagerTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self):
        super().__init__()
        
        #-----QTreeWidget Property settings-----
        self.setHeaderHidden(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.viewport().setAcceptDrops(True)
        
        #-----Bind context menu event to self.context_menu_requested-----
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_requested)
        
        #-----Get all avatar / prop / camera / light-----
        self.scene_objects = RLPy.RScene.FindObjects( RLPy.EObjectType_Avatar | RLPy.EObjectType_Prop | RLPy.EObjectType_Light | RLPy.EObjectType_Camera )
        self.items_dict = {} 

        #-----QTreeWidgetItem Property settings-----
        self.default_item = QtWidgets.QTreeWidgetItem()
        self.default_item.setText(0, "Layer_0")
        self.items_dict["Layer_0"] = {}
        self.items_dict["Layer_0"]["Layer_0"] = self.default_item
        self.default_item.setCheckState(0,Qt.Checked)
        self.addTopLevelItem(self.default_item)
        self.default_item.setFlags(self.default_item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable)
        
        #-----Create item for all scene objects-----
        for item in self.scene_objects:
            _name = item.GetName()
            temp_item = QtWidgets.QTreeWidgetItem()
            temp_item.setText(0, _name)
            temp_item.setCheckState(0,Qt.Checked)
            temp_item.setFlags(temp_item.flags() & ~Qt.ItemIsDropEnabled)

            self.items_dict["Layer_0"][_name] = temp_item
            self.default_item.addChild(temp_item)
            temp_item.setFlags(temp_item.flags() | Qt.ItemIsUserCheckable)

        self.itemChanged.connect(self.on_item_changed)
    
    def on_item_changed (self, current, previous):
        for key, value in self.items_dict.items():

            for key2, value2 in self.items_dict[key].items():
                if (value2.checkState(0)==Qt.Checked):
                    for item in self.scene_objects:
                        _name = item.GetName()
                        if (_name == key2):
                            RLPy.RScene.Show(item)
                else:
                    for item in self.scene_objects:
                        _name = item.GetName()
                        if (_name == key2):
                            RLPy.RScene.Hide(item)
                
    def context_menu_requested(self, pos):
        _menu = QtWidgets.QMenu()
        action = QtWidgets.QAction('Create Layer', self)
        action.triggered.connect(self.create_new_layer)
        _menu.addAction(action)
        _menu.exec_(self.mapToGlobal(pos))

    def create_new_layer(self):
        item = QtWidgets.QTreeWidgetItem()
        layer_name = 'Layer_'+str(len(self.items_dict))
        
        for k,v in self.items_dict.items():
            if (k == layer_name):
                layer_name = 'Layer_'+str(len(self.items_dict)+1)
        
        item.setText(0, layer_name)
        item.setCheckState(0,Qt.Checked)

        item.setFlags(item.flags() | Qt.ItemIsTristate | Qt.ItemIsUserCheckable | Qt.ItemIsEditable )

        self.addTopLevelItem(item)
        self.items_dict[layer_name] = {}
        self.items_dict[layer_name][layer_name] = item

def run_script(): 
    global layer_manager_dlg
    layer_manager_tree_widget = LayerManagerTreeWidget()
    
    layer_manager_dlg = RLPy.RUi.CreateRDockWidget()
    layer_manager_dlg.SetWindowTitle("Layer Manager")
    
    main_pyside_dlg = wrapInstance(int(layer_manager_dlg.GetWindow()), QtWidgets.QDockWidget)
    
    main_widget = QtWidgets.QWidget()
    
    main_pyside_dlg.setWidget(main_widget)
    
    main_widget_layout = QtWidgets.QVBoxLayout()
    
    main_widget.setLayout(main_widget_layout)
    
    
    label = QtWidgets.QLabel()
    label.setText("Right Click on the empty area to create a new layer.\nDrag the node to the new layer.\nDouble Click to rename the layer.")
    
    main_widget_layout.addWidget(label)
    main_widget_layout.addWidget(layer_manager_tree_widget)
    
    layer_manager_dlg.Show()
    
