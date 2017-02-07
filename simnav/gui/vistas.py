import logging
import sys
from functools import partial
from pathlib import Path

from PyQt5 import QtWidgets, QtCore, QtGui

from simnav.gui.base import Ui_VistaPrincipal, Ui_Configuracion, Ui_Composicion, Ui_Destilacion
from simnav.gui.utils import StdOutToTextBox, LogToStdOut


# TODO: REMUEVE TODOS LOS DRAG's
class VistaPrincipal(QtWidgets.QMainWindow):

    def __init__(self, simulacion):
        super().__init__()
        self.simulacion = simulacion
        # Logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = LogToStdOut()
        handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s: %(message)s'))
        self.logger.addHandler(handler)

        self.move(100, 100)
        self.build_ui()

        # Ventanas extra
        self.config = None
        self.conf_destilacion = None

        

    def build_ui(self):
        """Construye la interfaz de usuario a partir de la clase generada por qtdesigner"""
        self.ui = Ui_VistaPrincipal()
        self.ui.setupUi(self)

        #Configuracion extra
        self.ui.textBrowser.readOnly = True

        # Carpeta imagenes para buscar las imagenes
        imagen_torre = Path(__file__).parent / 'imagenes' / 'torre_destilacion.svg'
        self.ui.dibujoTorre.setPixmap(
            QtGui.QPixmap(str(imagen_torre)))
        

        # Redireccionando la salida de texto estandar al text browser
        sys.stdout = StdOutToTextBox(self.ui.textBrowser)

        # Conectando señales
        self.ui.actionCompuestos.triggered.connect(partial(self.abrir_configuracion, 0))
        self.ui.actionPropiedades.triggered.connect(partial(self.abrir_configuracion, 1))
        self.ui.actionCorrientes.triggered.connect(partial(self.abrir_configuracion, 2))
        self.ui.actionDestilacion.triggered.connect(self.abrir_conf_destilacion)

    def closeEvent(self, status):
        # Se sobreescribe esta funcion para que cierre todo el proceso al cerrar la ventana
        sys.exit()

    def abrir_configuracion(self, tab):
        self.config = Configuracion(self.simulacion, tab)

    def abrir_conf_destilacion(self):
        self.conf_destilacion = ConfiguracionDestilacion(self.simulacion)


class Configuracion(QtWidgets.QWidget):
    """Ventana de configuracion de simnav"""

    # Control de numeros de corriente para nombres
    numero_corriente = 1

    def __init__(self, simulacion, tab):
        super().__init__()
        self.simulacion = simulacion
        self.move(500, 100)

        # Interfaz
        self.ui = None
        self.build_ui(tab)

        # Ventanas extra
        self.modifica_composicion = None

        self.show()

    def build_ui(self, tab):
        """Construye la interfaz de usuario a partir de la clase generada por qtdesigner"""
        self.ui = Ui_Configuracion()
        self.ui.setupUi(self)
        self.ui.tabWidget.setCurrentIndex(tab)

        # Configuracion de la ui
        self.ui.compuestosTabla.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        # Señales
        # Tab Compuestos
        self.ui.buscarEdit.textEdited.connect(self.buscar)
        self.ui.agregarCompuesto.clicked.connect(self.agregar_compuesto)
        self.ui.eliminarCompuesto.clicked.connect(self.eliminar_compuesto)
        self.ui.borrarLista.clicked.connect(self.limpiar_lista)
        self.ui.compuestosTabla.cellDoubleClicked.connect(self.agregar_compuesto)
        self.ui.compuestosSeleccionadosList.itemDoubleClicked.connect(self.eliminar_compuesto)

        # Tab propiedades
        self.ui.paquetesDisponibles.itemDoubleClicked.connect(
            self.seleccionar_paquete_propiedades)

        # Tab corrientes
        self.ui.agregarCorriente.clicked.connect(self.crear_corriente)
        self.ui.eliminarCorriente.clicked.connect(self.eliminar_corriente)
        self.ui.listaCorrientes.itemClicked.connect(self.llenar_datos_corriente)
        self.ui.modificarComposicion.clicked.connect(self.modificar_composicion)
        self.ui.actualizarCorriente.clicked.connect(self.actualizar_corriente)

        # cargar datos de simulacion
        self._cargar_lista_compuestos()
        self._cargar_compuestos()
        self._cargar_paquete_propiedades()
        self._cargar_corrientes()

    def _cargar_compuestos(self):
        """Carga los compuestos de la simulacion a la lista de compuestos seleccionados"""
        for compuesto in self.simulacion.compuestos:
            self.ui.compuestosSeleccionadosList.addItem(compuesto)

    def _cargar_paquete_propiedades(self):
        """Carga el paquete de propiedades de la simulacion a la lista de paquete seleccionado"""
        if self.simulacion.paquete_propiedades:
            self.ui.paqueteSeleccionado.addItem(self.simulacion.paquete_propiedades.nombre)

    def _cargar_corrientes(self):
        """Carga las corrientes de la simulacion a la lista de corrientes"""
        for corriente in self.simulacion.corrientes:
            self.ui.listaCorrientes.addItem(corriente.nombre)

    def _cargar_lista_compuestos(self):
        """Cargar la lista de todos los compuestos disponibles en el simulador"""
        compuestos = self.simulacion.lista_compuestos()
        self.ui.compuestosTabla.setRowCount(len(compuestos))
        for fila, compuesto in enumerate(compuestos):
            self.ui.compuestosTabla.setItem(fila, 0,
                                            QtWidgets.QTableWidgetItem('Nombre Español'))
            self.ui.compuestosTabla.setItem(fila, 1,
                                            QtWidgets.QTableWidgetItem(compuesto.NAME))
            self.ui.compuestosTabla.setItem(fila, 2,
                                            QtWidgets.QTableWidgetItem(compuesto.FORMULA))

    def buscar(self, texto):
        """Busca compuesto de la lista de compuestos disponibles en la simulacion"""
        filas_buscadas = [item.row() for item in
                          self.ui.compuestosTabla.findItems(texto, QtCore.Qt.MatchStartsWith)]

        for fila in range(self.ui.compuestosTabla.rowCount()):
            if fila in filas_buscadas:
                self.ui.compuestosTabla.setRowHidden(fila, False)
            else:
                self.ui.compuestosTabla.setRowHidden(fila, True)

    def agregar_compuesto(self):
        """Agrega el compuesto seleccionado en la lista de compuestos disponibles
        a la lista de compuestos seleccionados y a la simulacion"""
        fila_seleccionada = self.ui.compuestosTabla.currentRow()
        if fila_seleccionada >= 0:
            # De la fila seleccionada se utiliza el nombre del componente en ingles
            compuesto_seleccionado = self.ui.compuestosTabla.item(fila_seleccionada, 1).text()
            # se chequea que el compuesto no este ya en la lista
            if compuesto_seleccionado not in self.simulacion.compuestos:
                self.simulacion.compuestos.append(compuesto_seleccionado)
                self.ui.compuestosSeleccionadosList.addItem(compuesto_seleccionado)

    def eliminar_compuesto(self):
        """Elimina el compuesto seleccionado de la lista de compuestos seleccionados
        y de la simulacion"""
        compuesto_seleccionado = self.ui.compuestosSeleccionadosList.currentRow()
        if compuesto_seleccionado >= 0:
            self.ui.compuestosSeleccionadosList.takeItem(compuesto_seleccionado)
            self.simulacion.compuestos.pop(compuesto_seleccionado)

    def limpiar_lista(self):
        """Elimina todos los compuestos de la lista de compuestos seleccionados y de la
        simulacion"""
        self.simulacion.compuestos.clear()
        for fila in range(self.ui.compuestosSeleccionadosList.count()):
            self.ui.compuestosSeleccionadosList.takeItem(0)

    def seleccionar_paquete_propiedades(self):
        """Agrega el paquete de propiedades seleccionado de la lista de paquetes disponibles
        a la lista de paquetes seleccioandos. Eliminando el paquete que pueda estar en la
        lista de paquetes seleccionados"""
        paquete_seleccionado = self.ui.paquetesDisponibles.currentItem().text()
        if paquete_seleccionado:
            # Solo puede ser seleccionado un paquete
            self.ui.paqueteSeleccionado.takeItem(0)
            self.ui.paqueteSeleccionado.addItem(paquete_seleccionado)
            self.simulacion.paquete_propiedades = paquete_seleccionado

    def _corriente_seleccionada(self):
        """Retorna la corriente seleccionada en la lista de corrientes"""
        pos_corriente = self.ui.listaCorrientes.currentRow()
        return self.simulacion.corrientes[pos_corriente]

    def crear_corriente(self):
        """Crea una corriente en la simulación y la agrega a la lista de corrientes"""
        nombre_corriente = f"Corriente {self.numero_corriente}"
        self.__class__.numero_corriente += 1

        self.simulacion.crear_corriente(nombre_corriente)
        self.ui.listaCorrientes.addItem(nombre_corriente)

    def eliminar_corriente(self):
        """Elimina la corriente seleccionada de la lista de corrientes y de la simulación"""
        pos_corriente = self.ui.listaCorrientes.currentRow()
        self.ui.listaCorrientes.takeItem(pos_corriente)
        del self.simulacion.corrientes[pos_corriente]

    def llenar_datos_corriente(self):
        """Toma los datos de la corriente seleccionada y los agrega a la forma de datos
        de corrientes"""
        corriente = self._corriente_seleccionada()

        self.ui.flujoLineEdit.setText(f'{corriente.flujo}')
        self.ui.temperaturaLineEdit.setText(f'{corriente.temperatura}')
        self.ui.presionLineEdit.setText(f'{corriente.presion}')

    def actualizar_corriente(self):
        """Actualiza los datos de la corriente seleccionada con los datos introducidos
        en la forma de datos de corriente"""
        flujo, temperatura, presion = (self.ui.flujoLineEdit.text(),
                                       self.ui.temperaturaLineEdit.text(),
                                       self.ui.presionLineEdit.text())

        corriente = self._corriente_seleccionada()
        corriente.flujo = flujo
        corriente.temperatura = temperatura
        corriente.presion = presion

    def modificar_composicion(self):
        """Abre el modificador de corriente si hay alguna corriente seleccionada"""
        corriente = self._corriente_seleccionada()
        if corriente:
            self.modifica_composicion = ModificaComposicion(corriente)

    def closeEvent(self, reason):
        self.simulacion.actualizar()
        super().closeEvent(reason)


class ModificaComposicion(QtWidgets.QWidget):
    def __init__(self, corriente):
        super().__init__()
        self.corriente = corriente

        # Ui
        self.ui = None
        self.build_ui()

        self.show()

    def build_ui(self):
        """Construye la interfaz de usuario a partir de la clase generada por qtdesigner"""
        self.ui = Ui_Composicion()
        self.ui.setupUi(self)
        self.ui.tablaComposicion.setRowCount(len(self.corriente.compuestos))
        for fila, (compuesto, fraccion) in enumerate(self.corriente):
            item_compuesto = QtWidgets.QTableWidgetItem(compuesto)
            item_compuesto.setFlags(QtCore.Qt.ItemIsEnabled)
            self.ui.tablaComposicion.setItem(fila, 0,
                                             item_compuesto)
            self.ui.tablaComposicion.setItem(fila, 1,
                                             QtWidgets.QTableWidgetItem(str(fraccion)))

        # Conectando señales
            self.ui.aceptar.clicked.connect(self.aceptar)
            self.ui.normalizar.clicked.connect(self.normalizar)

    def _range_table(self):
        yield from range(len(self.corriente.compuestos))

    def aceptar(self):
        """Acepta la composicion introducida -- normalizandola en el proceso."""
        self.normalizar()
        for fila in self._range_table():
            fraccion = float(self.ui.tablaComposicion.item(fila, 1).text())
            self.corriente.composicion[fila] = fraccion
        self.close()

    def normalizar(self):
        """Normaliza la composicion introducida (La sumatoria de las fracciones igual a 1)"""
        # Obteniendo la composicion
        composicion = []
        for fila in self._range_table():
            composicion.append(float(self.ui.tablaComposicion.item(fila, 1).text()))

        # Verificando la suma
        sum_composicion = sum(composicion)
        if sum_composicion != 1:
            for fila in self._range_table():
                # Se divide cada fraccion entre la sumatoria de ellas para normalizarla
                fraccion = float(self.ui.tablaComposicion.item(fila, 1).text())
                nueva_fraccion = str(round(fraccion/sum_composicion, 4))
                self.ui.tablaComposicion.item(fila, 1).setText(nueva_fraccion)
        else:
            return

class ConfiguracionDestilacion(QtWidgets.QWidget):
    #TODO: Cambiar titulo de ventana

    def __init__(self, simulacion):
        super().__init__()
        self.simulacion = simulacion

        self.build_ui()
        self.show()

    def build_ui(self):
        """Construye la interfaz de usuario a partir de la clase generada por qtdesigner"""
        self.ui = Ui_Destilacion()
        self.ui.setupUi(self)

        # Configuracion de la ui
        self.ui.tabWidget.setCurrentIndex(0)

        # Cargar simulacion
        self._cargar_datos_torre()
        self._cargar_corrientes()
        self._cargar_salidas_laterales()

    def _cargar_tipo_condensador(self, condensador):
        """Carga el tipo de condensador actual a la interfaz"""
        if condensador == "Parcial":
            self.ui.tipoDeCondensadorComboBox.setCurrentIndex(0)

        else:
            self.ui.tipoDeCondensadorComboBox.setCurrentIndex(1)

    def _cargar_corrientes(self):
        """Carga las corrientes de alimentaciones del destilador"""
        corrientes_entrada = self.simulacion.destilacion.corrientes_entrada
        for fila, (corriente, plato) in enumerate(corrientes_entrada):
            self.ui.tablaAlimentacion.setItem(fila, 0,
                                              QtWidgets.QTableWidgetItem(plato))
            self.ui.tablaAlimentacion.setItem(fila, 1,
                                              QtWidgets.QTableWidgetItem(corriente.nombre))

    def _cargar_salidas_laterales(self):
        """Carga las salidas laterales del simulador a la interfaz"""
        salidas_laterales = self.simulacion.destilacion.salidas_laterales
        for fila, (flujo, plato) in enumerate(salidas_laterales):
            self.ui.tablaAlimentacion.setItem(fila, 0,
                                              QtWidgets.QTableWidgetItem(plato))
            self.ui.tablaAlimentacion.setItem(fila, 1,
                                              QtWidgets.QTableWidgetItem(flujo))

    def _cargar_datos_torre(self):
        """Carga los parametros de la torre a la interfaz"""
        # Datos torre
        self.ui.numeroDePlatosLineEdit.setText(str(self.simulacion.destilacion.numero_platos))
        self.ui.presionLineEdit.setText(str(self.simulacion.destilacion.presion))
        self.ui.flujoDestiladoLineEdit.setText(str(self.simulacion.destilacion.destilado))
        self._cargar_tipo_condensador(self.simulacion.destilacion.condensador)
