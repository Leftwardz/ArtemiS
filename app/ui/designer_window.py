import os
import traceback
from datetime import datetime

import customtkinter as ctk
from tkinter import Canvas
from tkinter.filedialog import askopenfilename, asksaveasfilename

from app.services import admin_service
from app.services.designer_service import (
    ORIENTATION_LABELS,
    delete_product as designer_delete_product,
    has_unsaved_changes,
    load_product_drawings,
    orientation_index_from_label,
    save_product_with_drawings,
    validate_product_name,
)
from app.models.sheet_layout import CUSTOM_ORIENTATION_INDEX, SCOPE_SHEET, SCOPE_SLOT, SheetLayout
from app.services.layout_service import PAGE_PRESET_LABELS, build_grid_layout
from app.models.drawing_items import (
    BarcodeObject, BarcodeTextObject, CounterObject, ImageObject, LineObject,
    RectangleObject, SegmentLine, SegmentObject, TextObject, new_object_id,
)
from app.ui.designer_canvas_adapter import serialize_canvas_to_dict
from app.ui.drawing_store import (
    DrawingStore,
    make_barcode_object,
    make_barcode_text_object,
    make_image_object,
    make_line_object,
    make_rectangle_object,
    make_segment_object,
    make_text_object,
)
from app.ui.components import ConfirmWindow, ListBox, PopUpWindow, SpinBox, Tooltip
from app.ui.constants import (
    BTN_HOVER_RED,
    BTN_RED,
    FONT_LIST,
    ICON,
    PAPER_COLOR_LIST,
    PAPER_SIZE_TIP,
)
from app.utils.barcode_generator import (
    change_proportion,
    create_barcode,
    create_barcode39,
    create_datamatrix,
    create_qrcode,
    get_image,
)
from app.utils.text_utils import break_line
from app.utils.window_geometry import calculate_center_screen_with_monitor, get_monitor
from app.services.pdf_service import generate_test_pdf
from app.utils.document_delivery import open_path


class EditWindow(ctk.CTkToplevel):
    def __init__(self, master, mode, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.iconbitmap(ICON)
        ctk.deactivate_automatic_dpi_awareness()

        self.geometry(calculate_center_screen_with_monitor(master, 1220, 750, get_monitor(master)))
        self.minsize(1220, 750)
        self.maxsize(1220, 750)
        self.resizable(False, False)
        self.master = master
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.client = master.client_list.radio_var.get()
        self.id_selected_item = None
        self.copied_item = None
        self.set_title(master, mode)
        if mode == 'add':
            self.product_name = 'Novo Produto'
        else:
            self.product_name = master.product_list.radio_var.get()

        self.history = []

        # ------------------------ Name Frame ------------------------------------------------
        self.name_frame = ctk.CTkFrame(self, fg_color='transparent', width=500, height=100)
        self.name_frame.grid(row=0, column=0, columnspan=2, pady=10)

        ctk.CTkLabel(self.name_frame, text='Nome do produto:').grid(row=0, column=0, padx=10)

        self.entry_name_value = ctk.StringVar(value=self.product_name)
        self.entry_name = ctk.CTkEntry(self.name_frame, width=250, textvariable=self.entry_name_value)
        self.entry_name.grid(row=0, column=1, padx=10)

        self.btn_save = ctk.CTkButton(self.name_frame, text='Salvar', state='disabled', width=100,
                                      command=self.save_changes)
        self.btn_save.grid(row=0, column=2, padx=10)

        self.btn_delete = ctk.CTkButton(self.name_frame, text='Deletar', width=100,
                                        fg_color=BTN_RED,
                                        hover_color=BTN_HOVER_RED,
                                        command=self.confirm_delete)
        self.btn_delete.grid(row=0, column=3, padx=10)
        self.btn_visualize = ctk.CTkButton(self.name_frame, text='Visualizar', width=100,
                                           command=self.show_pdf, fg_color='#3F644B', hover_color='#688A76')
        self.btn_visualize.grid(row=0, column=4, padx=10)

        self.zoom_frame = ctk.CTkFrame(self.name_frame, fg_color='transparent')
        self.zoom_frame.grid(row=0, column=5, padx=10)
        ctk.CTkButton(self.zoom_frame, text='−', width=28, command=self.zoom_out).grid(row=0, column=0, padx=2)
        self.zoom_label = ctk.CTkLabel(self.zoom_frame, text='100%', width=46)
        self.zoom_label.grid(row=0, column=1, padx=2)
        ctk.CTkButton(self.zoom_frame, text='+', width=28, command=self.zoom_in).grid(row=0, column=2, padx=2)
        self.btn_zoom_reset = ctk.CTkButton(self.zoom_frame, text='100%', width=56, command=self.zoom_reset)
        self.btn_zoom_reset.grid(row=0, column=3, padx=(6, 2))

        self.lbl_id = ctk.CTkLabel(self, text=f'ID: {self.client} - {self.product_name}', font=('arial', 13, 'bold'))
        self.lbl_id.grid(row=1, column=0, columnspan=2, padx=10)

        # ------------------------ Buttons ------------------------------------------------

        self.btn_tools = ctk.CTkSegmentedButton(self,
                                                values=['Selecionar', 'Mover', 'Linha', 'Quadrado',
                                                        'Texto Fixo', 'Segmento', 'Código Barras', 'Imagem'],
                                                command=self.reset_all
                                                )
        self.btn_tools.grid(row=2, column=0, columnspan=2, padx=0, pady=0)
        self.btn_tools.set(value='Selecionar')


        # ------------------------ Paper Color --------------------------------------------
        self.frame_paper_color = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_paper_color.grid(row=2, column=1, padx=30, sticky='E')

        product = admin_service.get_db().search_product(self.client, self.product_name)
        if product:
            product_color = product.paper_color
            product_orientation = product.orientation
            product_paper_size = product.paper_size
            self.sheet_layout = SheetLayout.from_json(getattr(product, 'layout_config', None))
        else:
            product_orientation = '0'
            product_color = 'Branco'
            product_paper_size = '9'
            self.sheet_layout = SheetLayout.default()

        ctk.CTkLabel(self.frame_paper_color, text='Cor do Papel: ').grid(row=0, column=0, padx=2)
        self.paper_color_list = ctk.CTkComboBox(self.frame_paper_color, values=list(PAPER_COLOR_LIST.keys()),
                                                command=self.change_color)
        self.paper_color_list.grid(column=1, row=0)
        self.paper_color_list.set(product_color)

        self.color = ctk.CTkFrame(self.frame_paper_color, fg_color=PAPER_COLOR_LIST[product_color], width=30, height=30,
                                  corner_radius=0)
        self.color.grid(column=2, row=0, padx=5)

        # ------------------------ Paper Size --------------------------------------------
        self.frame_paper_size = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_paper_size.grid(row=1, column=1, padx=70, sticky='E')

        lbl_paper_size = ctk.CTkLabel(self.frame_paper_size, text='Tamanho Papel: ')
        lbl_paper_size.grid(row=0, column=0, padx=2)
        self.paper_size_list = ctk.CTkComboBox(self.frame_paper_size, values=[str(i) for i in range(21)],
                                               command=self.update_save_button)
        self.paper_size_list.grid(column=1, row=0)
        self.paper_size_list.set(product_paper_size)

        tooltip = Tooltip(lbl_paper_size, PAPER_SIZE_TIP)

        # ------------------------ Frame Choose Type Orientation --------------------------------------
        self.frame_type = ctk.CTkFrame(self, fg_color='transparent')
        self.frame_type.grid(row=2, column=0, padx=30, sticky='W')

        ctk.CTkLabel(self.frame_type, text='Orientação:').grid(row=0, column=0, padx=10)

        self.orient_values = ORIENTATION_LABELS

        self.combobox_type = ctk.CTkComboBox(self.frame_type, values=self.orient_values, width=180,
                                             command=self.change_orientation)
        self.combobox_type.grid(row=0, column=1)
        orient_idx = int(product_orientation) if str(product_orientation).isdigit() else 0
        if orient_idx >= len(self.orient_values):
            orient_idx = 0
        self.combobox_type.set(self.orient_values[orient_idx])
        product_orientation = str(orient_idx)

        self._build_custom_layout_panel()
        # ----------------------------- Canvas -------------------------------------------
        self.grid_rowconfigure(3, weight=1)

        # Resolution changes according to the orientation values from the product # see self.orient_values
        self.resolution = {
            '0': {'width': 1180, 'height': 560},  # 3 ARs Vertical -> Default
            '1': {'width': 590, 'height': 1680},  # 2 ARs Horizontal
            '2': {'width': 1180, 'height': 1680}, # Full A4 AR
            '3': {'width': 1180, 'height': 840}  # 2 ARs folha - Vertical
        }
        if product_orientation == str(CUSTOM_ORIENTATION_INDEX):
            canvas_width, canvas_height = self.sheet_layout.label_canvas_size()
        else:
            canvas_width = self.resolution[product_orientation]['width']
            canvas_height = self.resolution[product_orientation]['height']

        canvas_container = ctk.CTkFrame(self)
        canvas_container.grid(row=3, column=0, columnspan=5, padx=5, pady=10, sticky="nswe")
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)

        mode = ctk.get_appearance_mode()
        frame_fg = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        self.canvas_bg = frame_fg[0] if mode == 'Light' else frame_fg[1]

        self.canvas = Canvas(canvas_container, width=canvas_width, height=canvas_height,
                             bg=self.canvas_bg, highlightthickness=0,
                             scrollregion=(0, 0, canvas_width, canvas_height))
        self.canvas.grid(row=0, column=0, sticky="nswe")

        self.canvas_vbar = ctk.CTkScrollbar(canvas_container, orientation="vertical", command=self.canvas.yview)
        self.canvas_vbar.grid(row=0, column=1, sticky="ns")
        self.canvas_hbar = ctk.CTkScrollbar(canvas_container, orientation="horizontal", command=self.canvas.xview)
        self.canvas_hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=self.canvas_vbar.set, xscrollcommand=self.canvas_hbar.set)
        self.canvas.bind("<Configure>", self._update_view)

        self.canvas_images = []
        self.canvas_dict_images = {}
        self.drawing_store = DrawingStore()
        self.selected_items = []
        self.rubber_band = None
        self._rubber_add = False
        self.base_canvas_width = canvas_width
        self.base_canvas_height = canvas_height
        self.zoom = 1.0
        self.canvas_db_saved_items = self.consult_drawings_from_db()
        self.history.append(self.canvas_db_saved_items)
        self.lbl_testes = ctk.CTkLabel(self, text='X: , Y:', width=150)
        self.lbl_testes.grid(row=4, column=1, padx=10, sticky='SE')
        # --------------------- Variables and Windows ------------------------------------
        self.properties_window = ListOfPropertiesWindow(self)
        self.start_x = None
        self.start_y = None
        self.draw_object = None
        self.ctrl_z = None
        # ------------------------------- Events ----------------------------------------
        self.canvas.bind("<Button-1>", self.click_mouse_m1)
        self.canvas.bind("<B1-Motion>", self.move_mouse_m1)
        self.canvas.bind("<Motion>", self.canvas_mouse_motion)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_release_m1)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_wheel)
        self.bind("<Key>", self.keyboard_shortcuts)
        self.bind("<Control-c>", self.control_c)
        self.bind("<Control-C>", self.control_c)
        self.bind("<Control-z>", self.control_z)
        self.bind("<Control-Z>", self.control_z)
        self.bind("<Return>", self.reset_all)
        self.bind("<F4>", self.testes)
        self.bind("<Map>", self.bring_windows_back)
        self.bind("<Unmap>", self.minimize_windows)
        self.protocol("WM_DELETE_WINDOW", self.confirm_exit)

        # Any Event That Occurs
        self.entry_name.bind('<KeyRelease>', self.update_save_button)
        self.canvas.bind('<Button>', self.update_save_button)

        self.draw_items_into_canvas(self.canvas_db_saved_items)
        self._toggle_custom_layout_panel()
        self.focus_force()

    def _build_custom_layout_panel(self):
        layout = self.sheet_layout
        self.frame_custom_layout = ctk.CTkFrame(self.frame_type, fg_color='transparent')
        self.frame_custom_layout.grid(row=1, column=0, columnspan=2, padx=4, sticky='W')

        ctk.CTkLabel(self.frame_custom_layout, text='Layout customizado', font=('Arial', 13, 'bold')) \
            .grid(row=0, column=0, columnspan=8, sticky='W', pady=(0, 4))

        ctk.CTkLabel(self.frame_custom_layout, text='Folha:').grid(row=1, column=0, padx=4, sticky='E')
        self.custom_page_preset = ctk.CTkComboBox(
            self.frame_custom_layout, values=PAGE_PRESET_LABELS, width=120,
            command=self._on_custom_page_preset,
        )
        self.custom_page_preset.grid(row=1, column=1, padx=4, sticky='W')
        self.custom_page_preset.set(layout.page_preset)

        ctk.CTkLabel(self.frame_custom_layout, text='L×A folha (mm):').grid(row=1, column=2, padx=4, sticky='E')
        self.custom_page_w = ctk.CTkEntry(self.frame_custom_layout, width=60)
        self.custom_page_w.grid(row=1, column=3, padx=2)
        self.custom_page_w.insert(0, str(layout.page_width_mm))
        self.custom_page_h = ctk.CTkEntry(self.frame_custom_layout, width=60)
        self.custom_page_h.grid(row=1, column=4, padx=2)
        self.custom_page_h.insert(0, str(layout.page_height_mm))

        ctk.CTkLabel(self.frame_custom_layout, text='Etiqueta (mm):').grid(row=2, column=0, padx=4, sticky='E')
        self.custom_label_w = ctk.CTkEntry(self.frame_custom_layout, width=60)
        self.custom_label_w.grid(row=2, column=1, padx=2, sticky='W')
        self.custom_label_w.insert(0, str(layout.label_width_mm))
        self.custom_label_h = ctk.CTkEntry(self.frame_custom_layout, width=60)
        self.custom_label_h.grid(row=2, column=2, padx=2, sticky='W')
        self.custom_label_h.insert(0, str(layout.label_height_mm))

        ctk.CTkLabel(self.frame_custom_layout, text='Grade:').grid(row=2, column=3, padx=4, sticky='E')
        self.custom_cols = ctk.CTkEntry(self.frame_custom_layout, width=40)
        self.custom_cols.grid(row=2, column=4, padx=2)
        self.custom_cols.insert(0, str(layout.columns))
        ctk.CTkLabel(self.frame_custom_layout, text='×').grid(row=2, column=5)
        self.custom_rows = ctk.CTkEntry(self.frame_custom_layout, width=40)
        self.custom_rows.grid(row=2, column=6, padx=2)
        self.custom_rows.insert(0, str(layout.rows))

        ctk.CTkLabel(self.frame_custom_layout, text='Margens L/T/R/B (mm):').grid(row=3, column=0, padx=4, sticky='E')
        self.custom_margin_l = ctk.CTkEntry(self.frame_custom_layout, width=45)
        self.custom_margin_l.grid(row=3, column=1, padx=2)
        self.custom_margin_l.insert(0, str(layout.margin_left_mm))
        self.custom_margin_t = ctk.CTkEntry(self.frame_custom_layout, width=45)
        self.custom_margin_t.grid(row=3, column=2, padx=2)
        self.custom_margin_t.insert(0, str(layout.margin_top_mm))
        self.custom_margin_r = ctk.CTkEntry(self.frame_custom_layout, width=45)
        self.custom_margin_r.grid(row=3, column=3, padx=2)
        self.custom_margin_r.insert(0, str(layout.margin_right_mm))
        self.custom_margin_b = ctk.CTkEntry(self.frame_custom_layout, width=45)
        self.custom_margin_b.grid(row=3, column=4, padx=2)
        self.custom_margin_b.insert(0, str(layout.margin_bottom_mm))

        ctk.CTkLabel(self.frame_custom_layout, text='Espaço X/Y (mm):').grid(row=3, column=5, padx=4, sticky='E')
        self.custom_gap_x = ctk.CTkEntry(self.frame_custom_layout, width=45)
        self.custom_gap_x.grid(row=3, column=6, padx=2)
        self.custom_gap_x.insert(0, str(layout.gap_x_mm))
        self.custom_gap_y = ctk.CTkEntry(self.frame_custom_layout, width=45)
        self.custom_gap_y.grid(row=3, column=7, padx=2)
        self.custom_gap_y.insert(0, str(layout.gap_y_mm))

        self.custom_layout_status = ctk.CTkLabel(self.frame_custom_layout, text='', text_color='gray')
        self.custom_layout_status.grid(row=4, column=0, columnspan=8, sticky='W', padx=4, pady=(4, 0))

        self.frame_editor_scope = ctk.CTkFrame(self.frame_custom_layout, fg_color='transparent')
        self.frame_editor_scope.grid(row=5, column=0, columnspan=8, sticky='W', pady=(6, 0))
        ctk.CTkLabel(self.frame_editor_scope, text='Editar:').grid(row=0, column=0, padx=4)
        self.btn_editor_scope = ctk.CTkSegmentedButton(
            self.frame_editor_scope,
            values=['Etiqueta', 'Cabeçalho da folha'],
            command=self._on_editor_scope_button,
        )
        self.btn_editor_scope.grid(row=0, column=1, padx=4)
        self.btn_editor_scope.set('Etiqueta')
        self.editor_scope = SCOPE_SLOT

        for widget in (
            self.custom_page_w, self.custom_page_h, self.custom_label_w, self.custom_label_h,
            self.custom_cols, self.custom_rows, self.custom_margin_l, self.custom_margin_t,
            self.custom_margin_r, self.custom_margin_b, self.custom_gap_x, self.custom_gap_y,
        ):
            widget.bind('<KeyRelease>', self._on_custom_layout_change)

    def _is_custom_orientation(self):
        return self.combobox_type.get() == ORIENTATION_LABELS[CUSTOM_ORIENTATION_INDEX]

    def _toggle_custom_layout_panel(self):
        if self._is_custom_orientation():
            self.frame_custom_layout.grid()
            self._refresh_custom_layout_status()
            if hasattr(self, 'frame_editor_scope'):
                self.frame_editor_scope.grid()
        else:
            self.frame_custom_layout.grid_remove()
            if hasattr(self, 'frame_editor_scope'):
                self.frame_editor_scope.grid_remove()

    def _on_editor_scope_button(self, label):
        new_scope = SCOPE_SHEET if label == 'Cabeçalho da folha' else SCOPE_SLOT
        self._switch_editor_scope(new_scope)

    def _switch_editor_scope(self, new_scope):
        if new_scope == self.editor_scope:
            return
        self.pass_canvas_to_dict()
        self.clear_selection()
        self.editor_scope = new_scope
        label = 'Cabeçalho da folha' if new_scope == SCOPE_SHEET else 'Etiqueta'
        self.btn_editor_scope.set(label)
        w, h = self._editor_canvas_size()
        self.base_canvas_width = w
        self.base_canvas_height = h
        self.canvas.configure(width=w, height=h)
        self._redraw_editor_view()
        self.update_save_button()

    def _editor_canvas_size(self):
        if self._is_custom_orientation():
            layout = self._build_layout_from_form()
            if self.editor_scope == SCOPE_SHEET:
                return layout.page_canvas_size()
            return layout.label_canvas_size()
        index = self.orient_values.index(self.combobox_type.get())
        res = self.resolution[str(index)]
        return res['width'], res['height']

    def _active_editor_scope(self):
        if self._is_custom_orientation():
            return self.editor_scope
        return SCOPE_SLOT

    def _redraw_editor_view(self):
        """Redisena papel, guias de slot e objetos do escopo ativo."""
        for cid in list(self.canvas.find_all()):
            tags = self.canvas.gettags(cid)
            if 'paper' not in tags:
                self.canvas.delete(cid)
        self.canvas_dict_images.clear()
        self.drawing_store.canvas_to_object.clear()
        self.drawing_store._segment_canvas_lines.clear()
        self._update_view()
        if self._is_custom_orientation() and self.editor_scope == SCOPE_SHEET:
            layout = self._build_layout_from_form()
            for x1, y1, x2, y2 in layout.slot_guide_rects_logical():
                self.canvas.create_rectangle(
                    self._zs(x1), self._zs(y1), self._zs(x2), self._zs(y2),
                    outline='#aaaaaa', dash=(4, 4), width=1, tags=('slot_guide',),
                )
        for obj in self.drawing_store.objects_for_scope(self._active_editor_scope()):
            self._render_object(obj)
        self.canvas.tag_lower('slot_guide')
        self.canvas.tag_lower('paper')

    def _apply_editor_canvas_size(self):
        w, h = self._editor_canvas_size()
        self.base_canvas_width = w
        self.base_canvas_height = h
        self.canvas.configure(width=w, height=h)
        self._update_view()

    def _float_entry(self, entry, default):
        try:
            return float(str(entry.get()).replace(',', '.'))
        except (TypeError, ValueError):
            return default

    def _int_entry(self, entry, default):
        try:
            return int(float(str(entry.get()).replace(',', '.')))
        except (TypeError, ValueError):
            return default

    def _build_layout_from_form(self) -> SheetLayout:
        return build_grid_layout(
            page_preset=self.custom_page_preset.get(),
            page_width_mm=self._float_entry(self.custom_page_w, 210),
            page_height_mm=self._float_entry(self.custom_page_h, 297),
            label_width_mm=self._float_entry(self.custom_label_w, 100),
            label_height_mm=self._float_entry(self.custom_label_h, 50),
            columns=self._int_entry(self.custom_cols, 2),
            rows=self._int_entry(self.custom_rows, 2),
            margin_left_mm=self._float_entry(self.custom_margin_l, 5),
            margin_top_mm=self._float_entry(self.custom_margin_t, 5),
            margin_right_mm=self._float_entry(self.custom_margin_r, 5),
            margin_bottom_mm=self._float_entry(self.custom_margin_b, 5),
            gap_x_mm=self._float_entry(self.custom_gap_x, 2),
            gap_y_mm=self._float_entry(self.custom_gap_y, 2),
        )

    def _refresh_custom_layout_status(self):
        layout = self._build_layout_from_form()
        error = layout.validate()
        if error:
            self.custom_layout_status.configure(text=f'⚠ {error}', text_color='#c0392b')
        else:
            self.custom_layout_status.configure(
                text=f'{layout.slot_count} etiqueta(s) por folha — preenchimento sequencial',
                text_color='gray',
            )

    def _on_custom_layout_change(self, *_args):
        self._refresh_custom_layout_status()
        if self._is_custom_orientation():
            w, h = self._editor_canvas_size()
            if w != self.base_canvas_width or h != self.base_canvas_height:
                self.base_canvas_width = w
                self.base_canvas_height = h
                self.canvas.configure(width=w, height=h)
                self._redraw_editor_view()
        self.update_save_button()

    def _on_custom_page_preset(self, preset):
        from app.services.layout_service import PAGE_PRESETS
        if preset in PAGE_PRESETS and preset != 'Personalizado':
            w, h = PAGE_PRESETS[preset]
            self.custom_page_w.delete(0, 'end')
            self.custom_page_w.insert(0, str(w))
            self.custom_page_h.delete(0, 'end')
            self.custom_page_h.insert(0, str(h))
        self._on_custom_layout_change()

    def _current_layout_config_json(self):
        if not self._is_custom_orientation():
            return None
        return self._build_layout_from_form().to_json()

    def change_orientation(self, event):
        self.pass_canvas_to_dict()
        self._toggle_custom_layout_panel()
        if self._is_custom_orientation():
            layout = self._build_layout_from_form()
            error = layout.validate()
            if error:
                PopUpWindow(self, 'Layout inválido', error)
        else:
            self.editor_scope = SCOPE_SLOT
            if hasattr(self, 'btn_editor_scope'):
                self.btn_editor_scope.set('Etiqueta')

        self._apply_editor_canvas_size()
        self._redraw_editor_view()
        self.update_save_button()

    def change_color(self, event):
        color = self.paper_color_list.get()
        self.color.configure(fg_color=PAPER_COLOR_LIST[color])
        self.update_save_button()

    def set_title(self, master, mode):
        if mode == 'add':
            self.title(f'{self.client} - Novo Produto')
        elif mode == 'edit':
            product = master.product_list.radio_var.get()
            self.title(f'{self.client} - {product}')
        else:
            raise f'mode invalid: {mode}, use "edit" or "add"'

    def verify_changes(self):
        return has_unsaved_changes(
            self.client,
            self.product_name,
            self.entry_name.get(),
            self.paper_color_list.get(),
            orientation_index_from_label(self.combobox_type.get()),
            self.paper_size_list.get(),
            self.pass_canvas_to_dict(),
            self.consult_drawings_from_db(),
            admin_service.get_db(),
            layout_config=self._current_layout_config_json(),
        )

    def testes(self, *args):
        self.clean_canvas()

    def control_z(self, *args):
        if len(self.history) > 1:
            self.clean_canvas()
            self.history.pop()
            self.draw_items_into_canvas(self.history[-1])
            self.ctrl_z = True
            self.reset_all()

    def show_pdf(self, *args):
        try:
            orientation = self.orient_values.index(self.combobox_type.get())
            layout = self._build_layout_from_form() if orientation == CUSTOM_ORIENTATION_INDEX else None
            if layout:
                error = layout.validate()
                if error:
                    raise ValueError(error)
            generate_test_pdf(self.pass_canvas_to_dict(), orientation=orientation, layout=layout)
            open_path('temp/text.pdf')
        except PermissionError:
            PopUpWindow(self, 'Erro', 'Erro ao abrir o PDF, por favor fechar o aplicativo de PDF\n'
                                      'Ou configure o Navegador como aplicativo padrão de PDF')
        except ValueError as e:
            PopUpWindow(self, 'Erro', e)

        except Exception as e:
            PopUpWindow(self, 'Erro', traceback.format_exc())

    def consult_drawings_from_db(self):
        return load_product_drawings(self.client, self.product_name, admin_service.get_db())

    def update_save_button(self, *args):
        if self.verify_changes():
            self.btn_save.configure(state='normal')
        else:
            self.btn_save.configure(state='disabled')

    def confirm_delete(self):
        ConfirmWindow(self, 'Você tem certeza?', f'Você realmente deseja deletar o produto {self.product_name}?',
                      self.delete_product)

    def delete_product(self):
        if designer_delete_product(self.client, self.product_name, admin_service.get_db()):
            self.master.refresh()
            self.exit()
            PopUpWindow(self.master, 'Sucesso', 'Produto deletado com Sucesso!')
        else:
            error_msg = f'Não foi possível deletar o produto "{self.product_name}" do cliente "{self.client}"'
            PopUpWindow(self, 'Erro ao deletar', error_msg)

    def save_changes(self):
        try:
            validation_error = validate_product_name(
                self.product_name,
                self.entry_name.get(),
                admin_service.list_products(self.client),
            )
            if validation_error:
                raise ValueError(validation_error)

            color = self.paper_color_list.get()
            orientation_type = orientation_index_from_label(self.combobox_type.get())
            paper_size = self.paper_size_list.get()
            new_name = self.entry_name.get()

            save_product_with_drawings(
                self.client,
                self.product_name,
                new_name,
                color,
                orientation_type,
                paper_size,
                self.pass_canvas_to_dict(),
                admin_service.get_db(),
                layout_config=self._current_layout_config_json(),
            )

            self.product_name = new_name
            self.title(f'{self.client} - {self.product_name}')
            self.lbl_id.configure(text=f'ID: {self.client} - {self.product_name}')

            self.master.refresh()
            self.update_save_button()
            self.reset_all()
            PopUpWindow(self, 'Sucesso', 'Produto salvo com Sucesso!')
        except PermissionError:
            PopUpWindow(self, 'Erro', 'Erro ao abrir o PDF, por favor fechar o aplicativo de PDF\n'
                                      'Ou configure o Navegador como aplicativo padrão de PDF')
        except ValueError as e:
            PopUpWindow(self, 'Erro', e)

        except Exception as e:
            PopUpWindow(self, 'Erro', traceback.format_exc())

    def pass_canvas_to_dict(self, *args):
        return serialize_canvas_to_dict(
            self.canvas, self.canvas_dict_images, self.drawing_store,
            zoom=self.zoom, active_scope=self._active_editor_scope(),
        )

    def _group_canvas_ids(self, canvas_id):
        return self.drawing_store.group_canvas_ids(canvas_id)

    def _segment_tags(self, seg: SegmentObject, line):
        tags = list(seg.canvas_tags())
        if line.is_wrap:
            tags.append('wrap')
        return tags

    # ------------------------- Zoom: conversões lógico <-> tela ----------------------
    def _zs(self, value):
        """Lógico -> tela (multiplica pelo zoom)."""
        return float(value) * self.zoom

    def _zl(self, value):
        """Tela -> lógico (divide pelo zoom)."""
        return float(value) / self.zoom

    def _zfont(self, font_size):
        """Tamanho de fonte lógico -> tela."""
        try:
            return max(1, int(round(int(float(font_size)) * self.zoom)))
        except (TypeError, ValueError):
            return font_size

    def _render_segment(self, seg: SegmentObject):
        font = (seg.font_name, self._zfont(seg.font_size), seg.font_style)
        for line in seg.lines:
            cid = self.canvas.create_text(
                self._zs(line.x), self._zs(line.y), text=line.preview_text,
                fill='black', anchor='sw', justify='left',
                tags=self._segment_tags(seg, line),
                font=font, angle=seg.orientation,
            )
            self.drawing_store.bind_canvas(cid, seg.object_id)

    def _render_object(self, obj):
        if isinstance(obj, SegmentObject):
            self._render_segment(obj)
        elif isinstance(obj, LineObject):
            cid = self.canvas.create_line(
                self._zs(obj.x1), self._zs(obj.y1), self._zs(obj.x2), self._zs(obj.y2),
                width=obj.thickness, dash=obj.dashed or '',
                tags=obj.canvas_tags(),
            )
            self.drawing_store.bind_canvas(cid, obj.object_id)
        elif isinstance(obj, RectangleObject):
            cid = self.canvas.create_rectangle(
                self._zs(obj.x1), self._zs(obj.y1), self._zs(obj.x2), self._zs(obj.y2),
                width=obj.thickness, dash=obj.dashed or '',
                tags=obj.canvas_tags(),
            )
            self.drawing_store.bind_canvas(cid, obj.object_id)
        elif isinstance(obj, (TextObject, CounterObject)):
            cid = self.canvas.create_text(
                self._zs(obj.x), self._zs(obj.y), text=obj.text,
                font=(obj.font_name, self._zfont(obj.font_size), obj.font_style),
                angle=obj.orientation, anchor='sw',
                tags=obj.canvas_tags(),
            )
            self.drawing_store.bind_canvas(cid, obj.object_id)
        elif isinstance(obj, BarcodeObject):
            self._render_barcode(obj, companion_text=False)
        elif isinstance(obj, BarcodeTextObject):
            cid = self.canvas.create_text(
                self._zs(obj.x), self._zs(obj.y), text=obj.text,
                fill='black', font=(obj.font_name, self._zfont(obj.font_size), obj.font_style),
                angle=obj.orientation, anchor='sw',
                tags=obj.canvas_tags(),
            )
            self.drawing_store.bind_canvas(cid, obj.object_id)
        elif isinstance(obj, ImageObject):
            prop = int(obj.proportion)
            img = get_image(blob=obj.image_blob)
            img = change_proportion(img[2], int(round(prop * self.zoom)), orientation=int(obj.orientation))
            img[3] = prop
            cid = self.canvas.create_image(self._zs(obj.x), self._zs(obj.y), image=img[0],
                                           anchor='sw', tags=obj.canvas_tags())
            self.canvas_dict_images[cid] = img
            self.drawing_store.bind_canvas(cid, obj.object_id)

    def _render_barcode(self, obj: BarcodeObject, companion_text=True):
        text = obj.placeholder.replace('_', ' ')
        if obj.barcode_kind == 'barcode':
            create_barcode(text, obj.barcode_width, obj.barcode_height)
            img = get_image('temp/codigo_de_barras.png')
        elif obj.barcode_kind == 'barcode39':
            create_barcode39(text, obj.barcode_width, obj.barcode_height)
            img = get_image('temp/codigo_de_barras39.png')
        elif obj.barcode_kind == 'barcodeQR':
            create_qrcode(text)
            img = get_image('temp/qr_code.png')
        else:
            create_datamatrix(text)
            img = get_image('temp/dmtx.png')
        prop = int(obj.proportion)
        img = change_proportion(img[2], int(round(prop * self.zoom)), orientation=int(obj.orientation))
        img[3] = prop
        cid = self.canvas.create_image(
            self._zs(obj.x), self._zs(obj.y), image=img[0], tags=obj.canvas_tags(), anchor='sw',
        )
        self.canvas_dict_images[cid] = img
        self.drawing_store.bind_canvas(cid, obj.object_id)
        if companion_text and obj.barcode_kind in ('barcode', 'barcode39'):
            bt = make_barcode_text_object(
                int(obj.x), int(obj.y) + 22, text, obj.file_column, parent_id=obj.object_id,
            )
            bt.scope = obj.scope
            self.drawing_store.register(bt)
            tcid = self.canvas.create_text(
                self._zs(bt.x), self._zs(bt.y), text=text, fill='black',
                font=('arial', self._zfont(10), 'normal'), anchor='sw', tags=bt.canvas_tags(),
            )
            self.drawing_store.bind_canvas(tcid, bt.object_id)

    def draw_items_into_canvas(self, items):
        self.clean_canvas()
        self.drawing_store.load_from_db(items)
        if not self._is_custom_orientation():
            self.editor_scope = SCOPE_SLOT
        self._apply_editor_canvas_size()
        self._redraw_editor_view()

    # ------------------------------- Zoom -------------------------------------------
    def _paper_dims(self):
        return int(round(self.base_canvas_width * self.zoom)), int(round(self.base_canvas_height * self.zoom))

    def _update_view(self, event=None):
        """Ajusta a scrollregion (centralizando o papel) e (re)desenha o 'papel' branco."""
        pw, ph = self._paper_dims()
        if event is not None and event.width > 1:
            vw, vh = event.width, event.height
        else:
            vw, vh = self.canvas.winfo_width(), self.canvas.winfo_height()
        mx = max(0, (vw - pw) // 2)
        my = max(0, (vh - ph) // 2)
        self.canvas.configure(scrollregion=(-mx, -my, pw + mx, ph + my))
        self.canvas.delete('paper')
        pid = self.canvas.create_rectangle(0, 0, pw, ph, fill='white', outline='', tags='paper')
        self.canvas.tag_lower(pid)

    def _apply_canvas_size(self):
        self._update_view()

    def _redraw_from_store(self):
        """Redesenha todos os objetos do store no zoom atual (objetos = fonte de verdade)."""
        for cid in self.canvas.find_all():
            self.canvas.delete(cid)
        self.canvas_dict_images.clear()
        self.drawing_store.canvas_to_object.clear()
        self.drawing_store._segment_canvas_lines.clear()
        self._update_view()
        for obj in list(self.drawing_store.objects.values()):
            self._render_object(obj)

    def set_zoom(self, new_zoom):
        new_zoom = round(max(0.25, min(4.0, new_zoom)), 2)
        if abs(new_zoom - self.zoom) < 1e-3:
            return
        # 1) sincroniza objetos a partir do canvas no zoom atual (grava coords lógicas)
        self.pass_canvas_to_dict()
        # 2) guarda objetos selecionados
        sel_oids = []
        for rep in self.selected_items:
            obj = self.drawing_store.get_by_canvas(rep)
            if obj and obj.object_id not in sel_oids:
                sel_oids.append(obj.object_id)
        # 3) aplica zoom e redesenha
        self.zoom = new_zoom
        self._apply_canvas_size()
        self._redraw_editor_view()
        # 4) restaura seleção
        self.selected_items = []
        for oid in sel_oids:
            ids = self.drawing_store.canvas_ids_for_object(oid)
            if ids:
                rep = self._representative_canvas_id(ids[0])
                if rep not in self.selected_items:
                    self.selected_items.append(rep)
        self.id_selected_item = self.selected_items[-1] if self.selected_items else None
        if self.zoom_label is not None:
            self.zoom_label.configure(text=f'{int(round(self.zoom * 100))}%')
        self.refresh()
        self.properties_window.last_id = None
        self.properties_window.refresh()

    def zoom_in(self):
        self.set_zoom(self.zoom + 0.25)

    def zoom_out(self):
        self.set_zoom(self.zoom - 0.25)

    def zoom_reset(self):
        self.set_zoom(1.0)

    def _on_ctrl_wheel(self, event):
        self.set_zoom(round(self.zoom + (0.1 if event.delta > 0 else -0.1), 2))
        return 'break'

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), 'units')
        return 'break'

    def _on_shift_wheel(self, event):
        self.canvas.xview_scroll(int(-event.delta / 120), 'units')
        return 'break'

    def _event_xy(self, event):
        """Converte coords do evento (viewport) para coords de conteúdo do canvas (com scroll)."""
        event.x = int(self.canvas.canvasx(event.x))
        event.y = int(self.canvas.canvasy(event.y))
        return event

    @staticmethod
    def _advance_segment_xy(x, y, dist, orientation):
        if orientation == '90':
            return x + dist, y
        if orientation == '180':
            return x, y - dist
        if orientation == '270':
            return x - dist, y
        return x, y + dist

    def rebuild_segment_lines(self, seg: SegmentObject):
        """Recria linhas do segmento no canvas mantendo o mesmo object_id."""
        was_selected = self.id_selected_item in self.drawing_store.segment_canvas_ids(seg.object_id)
        for cid in list(self.drawing_store.segment_canvas_ids(seg.object_id)):
            self.drawing_store.unbind_canvas(cid)
            self.canvas.delete(cid)
        self._segment_canvas_lines_clear(seg.object_id)
        self._render_segment(seg)
        new_ids = self.drawing_store.segment_canvas_ids(seg.object_id)
        if was_selected:
            self.id_selected_item = new_ids[0] if new_ids else None
            self.properties_window.last_id = None

    def _segment_canvas_lines_clear(self, segment_id):
        self.drawing_store._segment_canvas_lines.pop(segment_id, None)

    def _rebuild_segment_preview_lines(self, seg: SegmentObject):
        """Recalcula linhas de preview a partir dos labels (mantém object_id)."""
        x, y = int(seg.anchor_x), int(seg.anchor_y)
        dist = int(seg.line_distance or 15)
        new_lines = []
        for label in seg.labels:
            parts = break_line(label, seg.char_limit)
            new_lines.append(SegmentLine(parts[0], str(x), str(y), is_wrap=False))
            if parts[1]:
                x, y = self._advance_segment_xy(x, y, dist, seg.orientation)
                new_lines.append(SegmentLine(parts[1], str(x), str(y), is_wrap=True))
            x, y = self._advance_segment_xy(x, y, dist, seg.orientation)
        seg.lines = new_lines
        if new_lines:
            seg.anchor_x, seg.anchor_y = new_lines[0].x, new_lines[0].y

    def register_new_canvas_item(self, canvas_id, obj):
        obj.scope = self._active_editor_scope()
        self.drawing_store.register(obj)
        self.drawing_store.bind_canvas(canvas_id, obj.object_id)

    # ------------------------- Seleção (single + múltipla) ---------------------------
    def _item_at(self, x, y):
        """Item registrado sob o cursor (topo), ou None se for área vazia."""
        items = self.canvas.find_overlapping(x - 2, y - 2, x + 2, y + 2)
        for cid in reversed(items):
            if cid == self.rubber_band:
                continue
            tags = self.canvas.gettags(cid)
            if 'slot_guide' in tags:
                continue
            if self.drawing_store.get_by_canvas(cid) is not None:
                return cid
        return None

    def _representative_canvas_id(self, canvas_id):
        """Canvas id 'líder' do objeto (1ª linha do segmento, ou o próprio)."""
        obj = self.drawing_store.get_by_canvas(canvas_id)
        if isinstance(obj, SegmentObject):
            ids = self.drawing_store.segment_canvas_ids(obj.object_id)
            return ids[0] if ids else canvas_id
        return canvas_id

    def all_selected_canvas_ids(self):
        result = []
        for rep in self.selected_items:
            for cid in self._group_canvas_ids(rep):
                if cid not in result:
                    result.append(cid)
        return result

    def select_single(self, canvas_id):
        rep = self._representative_canvas_id(canvas_id)
        self.selected_items = [rep]
        self.id_selected_item = rep

    def toggle_select(self, canvas_id):
        rep = self._representative_canvas_id(canvas_id)
        if rep in self.selected_items:
            self.selected_items.remove(rep)
        else:
            self.selected_items.append(rep)
        self.id_selected_item = self.selected_items[-1] if self.selected_items else None

    def clear_selection(self):
        self.selected_items = []
        self.id_selected_item = None

    def canvas_mouse_motion(self, event):
        self._event_xy(event)
        self.lbl_testes.configure(text=f"X: {event.x}, Y: {event.y}")

    def control_c(self, event):
        """Copia (duplica) todos os itens selecionados, deslocados, e os seleciona."""
        if not self.selected_items:
            return
        dx, dy = 10, 10
        new_reps = []
        for rep in list(self.selected_items):
            obj = self.drawing_store.get_by_canvas(rep)
            if obj is None:
                continue
            new_rep = self._clone_object(obj, dx, dy)
            if new_rep is not None:
                new_reps.append(new_rep)
        if new_reps:
            self.selected_items = new_reps
            self.id_selected_item = new_reps[-1]
        self.refresh()
        self.properties_window.refresh()

    def _clone_object(self, obj, dx, dy):
        """Clona um DrawingObject com offset; renderiza e retorna o canvas id líder."""
        from dataclasses import replace

        if isinstance(obj, SegmentObject):
            new = replace(
                obj,
                object_id=new_object_id('seg-'),
                columns=list(obj.columns),
                labels=list(obj.labels),
                lines=[],
                anchor_x=str(int(obj.anchor_x) + dx),
                anchor_y=str(int(obj.anchor_y) + dy),
            )
            self.drawing_store.register(new)
            self._rebuild_segment_preview_lines(new)
            self._render_segment(new)
        elif isinstance(obj, (TextObject, CounterObject)):
            prefix = 'cnt-' if isinstance(obj, CounterObject) else 'txt-'
            new = replace(obj, object_id=new_object_id(prefix),
                          x=str(int(obj.x) + dx), y=str(int(obj.y) + dy))
            self.drawing_store.register(new)
            self._render_object(new)
        elif isinstance(obj, LineObject):
            new = replace(obj, object_id=new_object_id('ln-'),
                          x1=str(int(float(obj.x1)) + dx), y1=str(int(float(obj.y1)) + dy),
                          x2=str(int(float(obj.x2)) + dx), y2=str(int(float(obj.y2)) + dy))
            self.drawing_store.register(new)
            self._render_object(new)
        elif isinstance(obj, RectangleObject):
            new = replace(obj, object_id=new_object_id('rect-'),
                          x1=str(int(float(obj.x1)) + dx), y1=str(int(float(obj.y1)) + dy),
                          x2=str(int(float(obj.x2)) + dx), y2=str(int(float(obj.y2)) + dy))
            self.drawing_store.register(new)
            self._render_object(new)
        elif isinstance(obj, BarcodeObject):
            new = replace(obj, object_id=new_object_id('bc-'),
                          x=str(int(obj.x) + dx), y=str(int(obj.y) + dy),
                          companion_text_id=None)
            self.drawing_store.register(new)
            self._render_barcode(new, companion_text=True)
        elif isinstance(obj, BarcodeTextObject):
            new = replace(obj, object_id=new_object_id('bct-'),
                          x=str(int(obj.x) + dx), y=str(int(obj.y) + dy),
                          parent_barcode_id=None)
            self.drawing_store.register(new)
            self._render_object(new)
        elif isinstance(obj, ImageObject):
            new = replace(obj, object_id=new_object_id('img-'),
                          x=str(int(obj.x) + dx), y=str(int(obj.y) + dy))
            self.drawing_store.register(new)
            self._render_object(new)
        else:
            return None

        ids = self.drawing_store.canvas_ids_for_object(new.object_id)
        return ids[0] if ids else None

    def keyboard_shortcuts(self, event):
        if not self.selected_items:
            return
        if event.keysym == 'Delete':
            self.delete_object()
            return
        moves = {'Left': (-1, 0), 'Right': (1, 0), 'Up': (0, -1), 'Down': (0, 1)}
        if event.keysym not in moves:
            return
        dx, dy = moves[event.keysym]
        for i in self.all_selected_canvas_ids():
            self.canvas.move(i, dx, dy)
        self.properties_window.update_xy_entrys()

    def minimize_windows(self, event):
        if hasattr(self, 'properties_window'):
            self.properties_window.iconify()

    def bring_windows_back(self, event):
        if hasattr(self, 'properties_window'):
            self.properties_window.deiconify()
            self.properties_window.lift()

    def delete_object(self):
        if not self.selected_items:
            return
        for rep in list(self.selected_items):
            obj = self.drawing_store.get_by_canvas(rep)
            for i in self._group_canvas_ids(rep):
                self.drawing_store.unbind_canvas(i)
                if i in self.canvas_dict_images:
                    del self.canvas_dict_images[i]
                self.canvas.delete(i)
            if obj:
                self.drawing_store.objects.pop(obj.object_id, None)
                if isinstance(obj, SegmentObject):
                    self._segment_canvas_lines_clear(obj.object_id)
        self.clear_selection()
        self.refresh()
        self.properties_window.refresh()

    def click_mouse_m1(self, event):
        self._event_xy(event)
        self.properties_window.wm_state('normal')
        self.properties_window.lift()
        self.start_x = event.x
        self.start_y = event.y
        if self.btn_tools.get() in ['Linha', 'Quadrado']:
            self.reset_all()

        elif self.btn_tools.get() in ['Selecionar', 'Mover']:
            ctrl = bool(event.state & 0x4)
            clicked = self._item_at(event.x, event.y)

            if clicked is not None:
                rep = self._representative_canvas_id(clicked)
                if ctrl:
                    self.toggle_select(clicked)
                elif rep in self.selected_items and len(self.selected_items) > 1:
                    # mantém multisseleção ao iniciar arraste (Mover)
                    self.id_selected_item = rep
                else:
                    self.select_single(clicked)
            else:
                if not ctrl:
                    self.clear_selection()
                self._rubber_add = ctrl
                self.rubber_band = self.canvas.create_rectangle(
                    event.x, event.y, event.x, event.y,
                    outline='#1f6aa5', dash=(3, 3),
                )
            self.refresh()
            self.properties_window.refresh()

        elif self.btn_tools.get() == 'Código Barras':
            GetBarcodeWindow(self, self.start_x, self.start_y)
            self.btn_tools.set(value='Mover')

        elif self.btn_tools.get() == 'Texto Fixo':
            GetTextWindow(self, self.start_x, self.start_y)
            self.refresh()
            self.properties_window.refresh()
            self.btn_tools.set(value='Mover')

        elif self.btn_tools.get() == 'Imagem':
            GetImageWindow(self, self.start_x, self.start_y)
            self.btn_tools.set(value='Mover')

        elif self.btn_tools.get() == 'Segmento':
            GetSegmentWindow(self, int(round(self._zl(self.start_x))), int(round(self._zl(self.start_y))))
            self.btn_tools.set(value='Mover')

    def move_mouse_m1(self, event):
        self._event_xy(event)
        self.lbl_testes.configure(text=f"X: {event.x}, Y: {event.y}")
        if self.btn_tools.get() == 'Linha':
            if self.draw_object:
                self.canvas.delete(self.draw_object)
            # If Shift is being Pressed
            if event.state & 0x1:
                if abs(self.start_x - event.x) > abs(self.start_y - event.y):
                    self.draw_object = self.canvas.create_line(self.start_x, self.start_y, event.x, self.start_y,
                                                               width=1)
                else:
                    self.draw_object = self.canvas.create_line(self.start_x, self.start_y, self.start_x, event.y,
                                                               width=1)
            else:
                self.draw_object = self.canvas.create_line(self.start_x, self.start_y, event.x, event.y, width=1)

        elif self.btn_tools.get() == 'Quadrado':
            if self.draw_object:
                self.canvas.delete(self.draw_object)
            self.draw_object = self.canvas.create_rectangle(self.start_x, self.start_y, event.x, event.y, width=1)

        elif self.rubber_band is not None:
            self.canvas.coords(self.rubber_band, self.start_x, self.start_y, event.x, event.y)

        elif self.btn_tools.get() == 'Mover' and self.selected_items:
            for i in self.all_selected_canvas_ids():
                self.canvas.move(i, event.x - self.start_x, event.y - self.start_y)
            self.start_x = event.x
            self.start_y = event.y

    def mouse_release_m1(self, event):
        self.update_save_button()
        if self.btn_tools.get() in ['Linha', 'Quadrado']:
            if self.draw_object is not None:
                coords = [self._zl(c) for c in self.canvas.coords(self.draw_object)]
                coords = [int(round(c)) for c in coords]
                if self.btn_tools.get() == 'Linha':
                    self.canvas.itemconfig(self.draw_object, fill='red')
                    ln = make_line_object(*coords, 1)
                    self.register_new_canvas_item(self.draw_object, ln)
                else:
                    self.canvas.itemconfig(self.draw_object, outline='red')
                    rect = make_rectangle_object(*coords, 1)
                    self.register_new_canvas_item(self.draw_object, rect)
                self.select_single(self.draw_object)
            self.btn_tools.set(value='Mover')

        elif self.rubber_band is not None:
            x1, y1, x2, y2 = self.canvas.coords(self.rubber_band)
            self.canvas.delete(self.rubber_band)
            self.rubber_band = None
            self._select_within(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2),
                                add=self._rubber_add)
            self._rubber_add = False

        self.refresh()
        self.properties_window.refresh()
        self.draw_object = None

    def _select_within(self, x1, y1, x2, y2, add=False):
        if abs(x2 - x1) < 3 and abs(y2 - y1) < 3:
            return
        enclosed = self.canvas.find_enclosed(x1, y1, x2, y2)
        reps = list(self.selected_items) if add else []
        for cid in enclosed:
            if self.drawing_store.get_by_canvas(cid) is None:
                continue
            rep = self._representative_canvas_id(cid)
            if rep not in reps:
                reps.append(rep)
        self.selected_items = reps
        self.id_selected_item = reps[-1] if reps else None

    def reset_all(self, *args):
        self.clear_selection()
        self.refresh()
        self.properties_window.refresh()

    def paint_object(self, object_id, color):
        if object_id:
            tags = self.canvas.gettags(object_id)
            if 'paper' in tags or 'slot_guide' in tags:
                return
        if object_id:
            for i in self._group_canvas_ids(object_id):
                if self.canvas.type(i) == 'rectangle':
                    self.canvas.itemconfig(i, outline=color)
                elif self.canvas.type(i) == 'image' and color == 'red':
                    self.canvas.itemconfig(i, image=self.canvas_dict_images[i][1])
                elif self.canvas.type(i) == 'image' and color == 'black':
                    self.canvas.itemconfig(i, image=self.canvas_dict_images[i][0])
                else:
                    self.canvas.itemconfig(i, fill=color)

    def refresh(self, *args):
        self.update_save_button()
        for i in self.canvas.find_all():
            self.paint_object(i, 'black')

        if self.pass_canvas_to_dict() != self.history[-1] and not self.ctrl_z:
            if len(self.history) > 10:
                self.history.pop(0)

            self.history.append(self.pass_canvas_to_dict())

        self.ctrl_z = None
        for rep in self.selected_items:
            self.paint_object(rep, 'red')

    def clean_canvas(self):
        for i in self.canvas.find_all():
            self.canvas.delete(i)
        self.canvas_dict_images.clear()
        self.drawing_store.clear()

    def confirm_exit(self):
        if self.verify_changes():
            ConfirmWindow(self, 'Produto não salvo', 'O produto não está salvo, você tem certeza?',
                          self.exit, has_confirm=False)
        else:
            self.exit()

    def exit(self):
        
        #ctk.activate_automatic_dpi_awareness()
        self.properties_window.destroy()
        self.destroy()
        self.master.focus_set()
        self.master.deiconify()


class ListOfPropertiesWindow(ctk.CTkToplevel):
    def __init__(self, master, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title('Lista de Propriedades')
        self.iconbitmap(ICON)
        self.width, self.height = 300, 550
        self.minsize(self.width, self.height)
        self.maxsize(self.width, self.height)
        self.resizable(False, False)
        self.master = master
        self.last_id = master.id_selected_item

        self.geometry(calculate_center_screen_with_monitor(master, 300, 550, get_monitor(master),
                                                           move_x=-470))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.validation = self.register(self.is_valid_input)
        self.frame = None
        self.panels = {}
        self.panel_refs = {}
        self._multi_count_label = None

        self.is_segment = False
        self.selected_object = None
        self.segment_obj = None
        self.is_counter = False
        self.segment_itens = []
        self.is_barcode = False
        self.barcode_obj = None
        self.barcode_width = None
        self.barcode_height = None
        self.barcode_column = None
        self.barcode_text_entry = None
        self.btn_rebuild_barcode = None
        # ---------------- Widgets for Text -----------------------------------------
        self.entry_x1 = None
        self.entry_y1 = None
        self.entry_x2 = None
        self.entry_y2 = None
        self.combobox_width = None
        self.combobox_dash = None
        self.font_family_combobox = None
        self.font_size_combobox = None
        self.font_style_combobox = None
        self.entry_text = None
        self.orientation = None
        self.distance = None
        self.char_limit = None
        self.btn_ok = None
        self.btn_cancel = None
        self.entry_proportion = None
        self.last_proportion = 100
        self.last_orientation = 0
        self.bind("<Return>", self.update_item)
        self.btn_save_img = None
        self.btn_lift_up = None
        self.btn_lift_down = None
        self.info_label = None
        self.panel_signature = None

        self.refresh()
        self.protocol('WM_DELETE_WINDOW', lambda: None)

    @staticmethod
    def is_valid_input(input_str):
        return input_str.isdigit() or input_str == ""

    def images_properties(self, selected_object):
        x, y = self.master.canvas.coords(selected_object)

        proportion = self.master.canvas_dict_images[selected_object][3]
        orientation = self.master.canvas_dict_images[selected_object][4]

        lbl_position_x = ctk.CTkLabel(self.frame, text='Posição X:')
        lbl_position_x.grid(row=0, column=0, padx=10, pady=10, sticky="W")

        self.entry_x1 = SpinBox(self.frame, func=self.update_item)
        self.entry_x1.grid(row=0, column=1, pady=10, padx=10)
        self.entry_x1.set(int(x))

        lbl_position_y = ctk.CTkLabel(self.frame, text='Posição Y:')
        lbl_position_y.grid(row=1, column=0, padx=10, pady=10, sticky="W")

        self.entry_y1 = SpinBox(self.frame, func=self.update_item)
        self.entry_y1.grid(row=1, column=1, pady=10, padx=10)
        self.entry_y1.set(int(y))

        ctk.CTkLabel(self.frame, text='Proporção').grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.entry_proportion = SpinBox(self.frame, func=self.update_item)
        self.entry_proportion.grid(row=2, column=1, pady=10, padx=10)
        self.entry_proportion.set(int(proportion))
        self.last_proportion = int(proportion)
        self.last_orientation = int(orientation)

        ctk.CTkLabel(self.frame, text='Orientação:').grid(row=3, column=0, padx=10, pady=10, sticky="W")
        self.orientation = ctk.CTkComboBox(self.frame, values=['0', '90', '180', '270'], width=100,
                                           command=self.update_item)
        self.orientation.grid(row=3, column=1, pady=10, padx=10)
        self.orientation.set(orientation)

        next_row = 4
        if self.is_barcode and self.barcode_obj:
            f = self.barcode_obj.file_column
            row = 4

            if self.barcode_obj.barcode_kind in ('barcode', 'barcode39'):
                ctk.CTkLabel(self.frame, text='Largura:').grid(row=row, column=0, padx=10, pady=10, sticky="W")
                barcode_widths = ['0.17', '0.18', '0.19', '0.20']
                self.barcode_width = ctk.CTkComboBox(self.frame, width=100, values=barcode_widths,
                                                     command=self.update_item)
                self.barcode_width.grid(row=row, column=1, pady=10, padx=10)
                self.barcode_width.set(self.barcode_obj.barcode_width)
                row += 1

                ctk.CTkLabel(self.frame, text='Altura:').grid(row=row, column=0, padx=10, pady=10, sticky="W")
                self.barcode_height = SpinBox(self.frame, func=self.update_item, step=0.1)
                self.barcode_height.grid(row=row, column=1, pady=10, padx=10)
                self.barcode_height.set(self.barcode_obj.barcode_height)
                row += 1

            # ------------------ Coluna (todos os tipos) ------------------------------------------------------
            ctk.CTkLabel(self.frame, text='Coluna:').grid(row=row, column=0, padx=10, pady=10, sticky="W")
            columns = [f'Coluna_{i}' for i in range(1, 100)]
            self.barcode_column = ctk.CTkComboBox(self.frame, width=100, values=columns,
                                                  command=self.update_item)
            self.barcode_column.grid(row=row, column=1, pady=10, padx=10)
            self.barcode_column.set(f)
            row += 1

            # ------------------ String do preview + reconstruir ----------------------------------------------
            ctk.CTkLabel(self.frame, text='String (preview):').grid(row=row, column=0, padx=10, pady=10, sticky="W")
            self.barcode_text_entry = ctk.CTkEntry(self.frame, width=120, justify='center')
            self.barcode_text_entry.grid(row=row, column=1, pady=10, padx=10)
            self.barcode_text_entry.insert(0, self.barcode_obj.placeholder)
            self.barcode_text_entry.bind('<Return>', self.rebuild_barcode)
            row += 1

            self.btn_rebuild_barcode = ctk.CTkButton(self.frame, text='Reconstruir preview', width=120,
                                                     command=self.rebuild_barcode)
            self.btn_rebuild_barcode.grid(row=row, column=0, columnspan=2, padx=10, pady=5)
            row += 1
            next_row = row

        self.btn_ok = ctk.CTkButton(self.frame, text='OK', width=100, command=self.update_item)
        self.btn_ok.grid(row=next_row, column=1, padx=10, pady=10)

        self.btn_cancel = ctk.CTkButton(self.frame, text='Deletar', fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
                                        width=100, command=self.master.delete_object)
        self.btn_cancel.grid(row=next_row, column=0, padx=10, pady=10)

        self.btn_lift_up = ctk.CTkButton(self.frame, text='Trazer para frente', width=100, command=self.bring_to_front)
        self.btn_lift_up.grid(row=next_row + 1, column=1, padx=10, pady=10)

        self.btn_lift_down = ctk.CTkButton(self.frame, text='Enviar para trás', width=100, command=self.send_to_back)
        self.btn_lift_down.grid(row=next_row + 1, column=0, padx=10, pady=10)

        self.btn_save_img = ctk.CTkButton(self.frame, text='Salvar Imagem', width=100, command=self.save_img)
        self.btn_save_img.grid(row=next_row + 2, column=0, columnspan=2, padx=10, pady=10)

        self._show_object_info(row=next_row + 3)
        self._fill_image_values(selected_object)

    def _object_info_text(self):
        obj = self.selected_object
        if obj:
            info = f'{obj.item_type}  id={obj.object_id}'
            if isinstance(obj, SegmentObject):
                info += f'\nColunas: {".".join(obj.columns)}'
            return info
        return str(self.master.canvas.gettags(self.master.id_selected_item))

    def _show_object_info(self, row):
        info_frame = ctk.CTkScrollableFrame(self.frame, height=40, orientation='horizontal')
        info_frame.grid(row=row, column=0, columnspan=2, padx=10, pady=10)
        self.info_label = ctk.CTkLabel(
            info_frame, text=self._object_info_text(),
            font=(FONT_LIST[0] if FONT_LIST else 'Arial', 10),
        )
        self.info_label.pack()

    def line_properties(self, selected_object):
        x1, y1, x2, y2 = [int(i) for i in self.master.canvas.coords(selected_object)]
        line_width = int(float(self.master.canvas.itemconfig(selected_object, 'width')[4]))
        dash = self.master.canvas.itemconfig(selected_object, 'dash')[4]
        dash = '0' if not dash else dash
        dash_values = {'0': 'Normal', '4': 'Pequeno', '40': 'Grande'}

        lbl_width = ctk.CTkLabel(self.frame, text='Espessura:')
        lbl_width.grid(row=0, column=0, padx=10, pady=10, sticky="W")

        self.combobox_width = ctk.CTkComboBox(self.frame, width=100, values=list(map(str, range(1, 10))),
                                              command=self.update_item)
        self.combobox_width.grid(row=0, column=1, padx=10, pady=10)
        self.combobox_width.set(line_width)

        lbl_dash = ctk.CTkLabel(self.frame, text='Traçejado:')
        lbl_dash.grid(row=1, column=0, padx=10, pady=10, sticky="W")

        self.combobox_dash = ctk.CTkComboBox(self.frame, width=100, values=list(dash_values.values()),
                                             command=self.update_item)
        self.combobox_dash.grid(row=1, column=1, padx=10, pady=10)
        self.combobox_dash.set(dash_values[dash])

        lbl_x_initial = ctk.CTkLabel(self.frame, text='Posição X1:')
        lbl_x_initial.grid(row=2, column=0, padx=10, pady=10, sticky="W")

        self.entry_x1 = SpinBox(self.frame, func=self.update_item)
        self.entry_x1.grid(row=2, column=1, padx=10, pady=10)
        self.entry_x1.set(int(x1))

        lbl_x_initial = ctk.CTkLabel(self.frame, text='Posição Y1:')
        lbl_x_initial.grid(row=3, column=0, padx=10, pady=10, sticky="W")

        self.entry_y1 = SpinBox(self.frame, func=self.update_item)
        self.entry_y1.grid(row=3, column=1, padx=10, pady=10)
        self.entry_y1.set(int(y1))

        lbl_y_final = ctk.CTkLabel(self.frame, text='Posição X2:')
        lbl_y_final.grid(row=4, column=0, padx=10, pady=10, sticky="W")

        self.entry_x2 = SpinBox(self.frame, func=self.update_item)
        self.entry_x2.grid(row=4, column=1, padx=10, pady=10)
        self.entry_x2.set(int(x2))

        lbl_y_final = ctk.CTkLabel(self.frame, text='Posição Y2:')
        lbl_y_final.grid(row=5, column=0, padx=10, pady=10, sticky="W")

        self.entry_y2 = SpinBox(self.frame, func=self.update_item)
        self.entry_y2.grid(row=5, column=1, padx=10, pady=10)
        self.entry_y2.set(int(y2))

        self.btn_ok = ctk.CTkButton(self.frame, text='OK', width=100, command=self.update_item)
        self.btn_ok.grid(row=6, column=1, padx=10, pady=10)

        self.btn_cancel = ctk.CTkButton(self.frame, text='Deletar', fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
                                        width=100, command=self.master.delete_object)
        self.btn_cancel.grid(row=6, column=0, padx=10, pady=10)

        self._show_object_info(row=7)
        self._fill_line_values(selected_object)

    def text_properties(self, selected_object):
        fonte = self.master.canvas.itemconfig(selected_object, 'font')[4]
        if '{' in fonte:
            fontname = fonte.split('}')[0].replace('{', '')
            fontsize = fonte.split('}')[1].split()[0]
            font_style = fonte.split('}')[1].split()[1]
            fonte = [fontname, fontsize, font_style]
        else:
            fonte = self.master.canvas.itemconfig(selected_object, 'font')[4].split()
        texto = self.master.canvas.itemconfig(selected_object, 'text')[4]
        orientacao = self.master.canvas.itemconfig(selected_object, 'angle')[4].replace('.0', '')
        font_family = fonte[0]
        font_size = fonte[1]
        font_style = fonte[2]

        if self.is_segment:
            x, y = self.master.canvas.coords(self.segment_itens[0])
        else:
            x, y = self.master.canvas.coords(selected_object)

        ctk.CTkLabel(self.frame, text='Fonte:').grid(row=0, column=0, padx=10, pady=10, sticky="W")
        self.font_family_combobox = ctk.CTkComboBox(self.frame, values=FONT_LIST, width=100, command=self.update_item)
        self.font_family_combobox.grid(row=0, column=1, pady=10, padx=10)
        self.font_family_combobox.set(font_family)

        ctk.CTkLabel(self.frame, text='Tamanho:').grid(row=1, column=0, padx=10, pady=10, sticky="W")
        self.font_size_combobox = ctk.CTkComboBox(self.frame, width=100, values=list(map(str, range(6, 28))),
                                                  command=self.update_item)
        self.font_size_combobox.grid(row=1, column=1, pady=10, padx=10)
        self.font_size_combobox.set(font_size)

        ctk.CTkLabel(self.frame, text='Estilo:').grid(row=2, column=0, padx=10, pady=10, sticky="W")
        self.font_style_combobox = ctk.CTkComboBox(self.frame, values=['Bold', 'Normal'], width=100,
                                                   command=self.update_item)
        self.font_style_combobox.grid(row=2, column=1, pady=10, padx=10)
        self.font_style_combobox.set(font_style.capitalize())

        ctk.CTkLabel(self.frame, text='Orientação:').grid(row=3, column=0, padx=10, pady=10, sticky="W")
        self.orientation = ctk.CTkComboBox(self.frame, values=['0', '90', '180', '270'], width=100,
                                           command=self.update_item)
        self.orientation.grid(row=3, column=1, pady=10, padx=10)
        self.orientation.set(orientacao)
        if self.is_segment and self.segment_obj:
            segment_distance = self.segment_obj.line_distance
            char_limit = self.segment_obj.char_limit

            ctk.CTkLabel(self.frame, text='Distância Entre linhas:').grid(row=4, column=0, padx=10, pady=10, sticky="W")
            self.distance = SpinBox(self.frame, func=self.update_item)
            self.distance.grid(row=4, column=1, pady=10, padx=10)
            self.distance.set(segment_distance)

            ctk.CTkLabel(self.frame, text='Limite Caracteres:').grid(row=5, column=0, padx=10, pady=10, sticky="W")
            self.char_limit = SpinBox(self.frame, func=self.update_item)
            self.char_limit.grid(row=5, column=1, pady=10, padx=10)
            self.char_limit.set(char_limit)

            self.btn_edit_segment = ctk.CTkButton(
                self.frame, text='Editar colunas', width=120,
                command=self.open_segment_editor,
            )
            self.btn_edit_segment.grid(row=8, column=0, columnspan=2, padx=10, pady=5)

        pos_row = 6 if not self.is_segment else 6
        ctk.CTkLabel(self.frame, text='Posição X:').grid(row=pos_row, column=0, padx=10, pady=10, sticky="W")
        self.entry_x1 = SpinBox(self.frame, func=self.update_item)
        self.entry_x1.grid(row=pos_row, column=1, pady=10, padx=10)
        self.entry_x1.set(int(x))

        ctk.CTkLabel(self.frame, text='Posição Y:').grid(row=pos_row + 1, column=0, padx=10, pady=10, sticky="W")
        self.entry_y1 = SpinBox(self.frame, func=self.update_item)
        self.entry_y1.grid(row=pos_row + 1, column=1, pady=10, padx=10)
        self.entry_y1.set(int(y))

        if not self.is_barcode and not self.is_counter and not self.is_segment:
            ctk.CTkLabel(self.frame, text='Texto').grid(row=pos_row + 2, column=0, columnspan=2, padx=10)

            self.entry_text = ctk.CTkEntry(self.frame, width=self.width - 80, justify='center')
            self.entry_text.grid(row=pos_row + 3, column=0, columnspan=2, padx=10, pady=5)
            self.entry_text.configure(textvariable=ctk.StringVar(value=texto))
            self.entry_text.bind("<KeyRelease>", self.update_item)

        btn_row = pos_row + 4 if not self.is_segment else 9
        self.btn_ok = ctk.CTkButton(self.frame, text='OK', width=100, command=self.update_item)
        self.btn_ok.grid(row=btn_row, column=1, padx=10, pady=10)

        self.btn_cancel = ctk.CTkButton(self.frame, text='Deletar', fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
                                        width=100, command=self.master.delete_object)
        self.btn_cancel.grid(row=btn_row, column=0, padx=10, pady=10)

        self._show_object_info(row=btn_row + 1)
        self._fill_text_values(selected_object)

    def open_segment_editor(self):
        if self.segment_obj:
            GetSegmentWindow(self.master, int(self.segment_obj.anchor_x), int(self.segment_obj.anchor_y),
                             edit_segment=self.segment_obj)

    def _set_selection_flags(self):
        self.selected_object = self.master.drawing_store.get_by_canvas(self.master.id_selected_item)
        self.is_segment = isinstance(self.selected_object, SegmentObject)
        self.is_barcode = isinstance(self.selected_object, BarcodeObject)
        self.is_counter = isinstance(self.selected_object, CounterObject)
        self.barcode_obj = self.selected_object if self.is_barcode else None
        if self.is_segment:
            self.segment_obj = self.selected_object
            self.segment_itens = self.master.drawing_store.segment_canvas_ids(self.segment_obj.object_id)
        else:
            self.segment_obj = None
            self.segment_itens = []

    def _selection_signature(self):
        """Assinatura do layout do painel — itens com mesma assinatura reaproveitam widgets."""
        canvas_type = self.master.canvas.type(self.master.id_selected_item)
        if canvas_type == 'text':
            return ('text', self.is_segment, self.is_counter)
        if canvas_type == 'image':
            kind = self.barcode_obj.barcode_kind if self.barcode_obj else None
            return ('image', kind)
        if canvas_type in ('line', 'rectangle'):
            return ('lr',)
        return (canvas_type,)

    def _panel_widgets_alive(self):
        try:
            return self.entry_x1 is not None and self.entry_x1.winfo_exists()
        except Exception:
            return False

    def _fill_current_panel(self):
        """Atualiza apenas os valores do painel atual (sem reconstruir widgets)."""
        sig = self.panel_signature
        item_id = self.master.id_selected_item
        if not sig:
            return
        if sig[0] == 'text':
            self._fill_text_values(item_id)
        elif sig[0] == 'image':
            self._fill_image_values(item_id)
        elif sig[0] == 'lr':
            self._fill_line_values(item_id)
        if self.info_label is not None:
            try:
                self.info_label.configure(text=self._object_info_text())
            except Exception:
                pass

    def _fill_text_values(self, selected_object):
        fonte = self.master.canvas.itemconfig(selected_object, 'font')[4]
        if '{' in fonte:
            fontname = fonte.split('}')[0].replace('{', '')
            rest = fonte.split('}')[1].split()
            fonte = [fontname, rest[0], rest[1] if len(rest) > 1 else 'normal']
        else:
            fonte = fonte.split()
        texto = self.master.canvas.itemconfig(selected_object, 'text')[4]
        orientacao = self.master.canvas.itemconfig(selected_object, 'angle')[4].replace('.0', '')
        z = self.master.zoom
        if self.is_segment and self.segment_itens:
            x, y = self.master.canvas.coords(self.segment_itens[0])
        else:
            x, y = self.master.canvas.coords(selected_object)
        self.font_family_combobox.set(fonte[0])
        self.font_size_combobox.set(str(max(1, int(round(int(float(fonte[1])) / z)))))
        self.font_style_combobox.set(fonte[2].capitalize())
        self.orientation.set(orientacao)
        if self.is_segment and self.segment_obj:
            self.distance.set(self.segment_obj.line_distance)
            self.char_limit.set(self.segment_obj.char_limit)
        self.entry_x1.set(int(round(x / z)))
        self.entry_y1.set(int(round(y / z)))
        if self.entry_text is not None and not self.is_barcode and not self.is_counter and not self.is_segment:
            self.entry_text.delete(0, 'end')
            self.entry_text.insert(0, texto)

    def _fill_line_values(self, selected_object):
        z = self.master.zoom
        x1, y1, x2, y2 = [int(round(i / z)) for i in self.master.canvas.coords(selected_object)]
        line_width = int(float(self.master.canvas.itemconfig(selected_object, 'width')[4]))
        dash = self.master.canvas.itemconfig(selected_object, 'dash')[4]
        dash = '0' if not dash else dash
        dash_values = {'0': 'Normal', '4': 'Pequeno', '40': 'Grande'}
        self.combobox_width.set(line_width)
        self.combobox_dash.set(dash_values.get(dash, 'Normal'))
        self.entry_x1.set(x1)
        self.entry_y1.set(y1)
        self.entry_x2.set(x2)
        self.entry_y2.set(y2)

    def _fill_image_values(self, selected_object):
        z = self.master.zoom
        x, y = self.master.canvas.coords(selected_object)
        proportion = self.master.canvas_dict_images[selected_object][3]
        orientation = self.master.canvas_dict_images[selected_object][4]
        self.entry_x1.set(int(round(x / z)))
        self.entry_y1.set(int(round(y / z)))
        self.entry_proportion.set(int(proportion))
        self.orientation.set(orientation)
        self.last_proportion = int(proportion)
        self.last_orientation = int(orientation)
        if self.is_barcode and self.barcode_obj:
            if self.barcode_width is not None:
                self.barcode_width.set(self.barcode_obj.barcode_width)
                self.barcode_height.set(self.barcode_obj.barcode_height)
            if self.barcode_column is not None:
                self.barcode_column.set(self.barcode_obj.file_column)
            if self.barcode_text_entry is not None:
                self.barcode_text_entry.delete(0, 'end')
                self.barcode_text_entry.insert(0, self.barcode_obj.placeholder)

    _PANEL_REF_NAMES = (
        'entry_x1', 'entry_y1', 'entry_x2', 'entry_y2',
        'combobox_width', 'combobox_dash',
        'font_family_combobox', 'font_size_combobox', 'font_style_combobox',
        'entry_text', 'orientation', 'distance', 'char_limit',
        'entry_proportion', 'barcode_width', 'barcode_height', 'barcode_column',
        'barcode_text_entry', 'btn_rebuild_barcode',
        'info_label', 'btn_ok', 'btn_cancel', 'btn_lift_up', 'btn_lift_down', 'btn_save_img',
    )

    @staticmethod
    def _frame_alive(frame):
        try:
            return frame is not None and frame.winfo_exists()
        except Exception:
            return False

    def _reset_panel_refs(self):
        for name in self._PANEL_REF_NAMES:
            setattr(self, name, None)

    def _snapshot_panel_refs(self):
        return {name: getattr(self, name) for name in self._PANEL_REF_NAMES}

    def _restore_panel_refs(self, refs):
        for name in self._PANEL_REF_NAMES:
            setattr(self, name, refs.get(name))

    def _hide_current_frame(self):
        if self._frame_alive(self.frame):
            try:
                self.frame.grid_remove()
            except Exception:
                pass

    def _show_panel(self, sig):
        """Mostra o painel da assinatura, reaproveitando do cache ou construindo na primeira vez."""
        self._hide_current_frame()
        self.panel_signature = sig
        cached = self.panels.get(sig)
        if self._frame_alive(cached):
            self.frame = cached
            self._restore_panel_refs(self.panel_refs.get(sig, {}))
            self.frame.grid(row=0, column=0, padx=10, pady=10)
            self._fill_current_panel()
            return
        frame = ctk.CTkFrame(self, width=280, height=self.height - 20, fg_color='transparent')
        frame.grid(row=0, column=0, padx=10, pady=10)
        self.frame = frame
        self._reset_panel_refs()
        canvas_type = self.master.canvas.type(self.master.id_selected_item)
        if canvas_type == 'text':
            self.text_properties(self.master.id_selected_item)
        elif canvas_type in ('line', 'rectangle'):
            self.line_properties(self.master.id_selected_item)
        elif canvas_type == 'image':
            self.images_properties(self.master.id_selected_item)
        self.panels[sig] = frame
        self.panel_refs[sig] = self._snapshot_panel_refs()

    def _activate_single_panel(self):
        if (self.master.id_selected_item == self.last_id
                and self._frame_alive(self.frame) and self._panel_widgets_alive()):
            self.update_xy_entrys()
            return
        self._set_selection_flags()
        sig = self._selection_signature()
        self.last_id = self.master.id_selected_item
        if sig == self.panel_signature and self._frame_alive(self.frame) and self._panel_widgets_alive():
            self._fill_current_panel()
            return
        self._show_panel(sig)

    def _activate_multi_panel(self):
        self.last_id = ('multi', tuple(self.master.selected_items))
        text = f'{len(self.master.selected_items)} itens selecionados'
        if self.panel_signature == ('multi',) and self._frame_alive(self.frame):
            if self._multi_count_label is not None:
                self._multi_count_label.configure(text=text)
            return
        self._hide_current_frame()
        self.panel_signature = ('multi',)
        self._reset_panel_refs()
        cached = self.panels.get(('multi',))
        if self._frame_alive(cached):
            self.frame = cached
            if self._multi_count_label is not None:
                self._multi_count_label.configure(text=text)
            self.frame.grid(row=0, column=0, padx=10, pady=10)
            return
        frame = ctk.CTkFrame(self, width=280, height=self.height - 20, fg_color='transparent')
        frame.grid(row=0, column=0, padx=10, pady=10)
        frame.rowconfigure(0, weight=1)
        self.frame = frame
        self._multi_count_label = ctk.CTkLabel(frame, text=text, font=('Lato', 16, 'bold'))
        self._multi_count_label.grid(row=0, column=0, padx=20, pady=20, sticky='N')
        ctk.CTkLabel(
            frame, text='Use as setas para mover,\nCtrl+C para copiar,\nDelete para apagar.',
            font=('Lato', 12),
        ).grid(row=1, column=0, padx=20)
        ctk.CTkButton(
            frame, text='Copiar (Ctrl+C)', width=120,
            command=lambda: self.master.control_c(None),
        ).grid(row=2, column=0, padx=10, pady=10)
        ctk.CTkButton(
            frame, text='Deletar', width=120, fg_color=BTN_RED, hover_color=BTN_HOVER_RED,
            command=self.master.delete_object,
        ).grid(row=3, column=0, padx=10, pady=5)
        self.panels[('multi',)] = frame

    def _activate_none_panel(self):
        self.last_id = None
        if self.panel_signature == ('none',) and self._frame_alive(self.frame):
            return
        self._hide_current_frame()
        self.panel_signature = ('none',)
        self._reset_panel_refs()
        cached = self.panels.get(('none',))
        if self._frame_alive(cached):
            self.frame = cached
            self.frame.grid(row=0, column=0, padx=10, pady=10)
            return
        frame = ctk.CTkFrame(self, width=280, height=self.height - 20, fg_color='transparent')
        frame.grid(row=0, column=0, padx=10, pady=10)
        frame.rowconfigure(0, weight=1)
        self.frame = frame
        ctk.CTkLabel(frame, text='Nenhum item selecionado', font=('Lato', 16, 'bold')).grid(
            row=0, column=0, padx=30, sticky='NSWE')
        self.panels[('none',)] = frame

    def refresh(self):
        if len(self.master.selected_items) > 1:
            self._activate_multi_panel()
        elif self.master.id_selected_item:
            self._activate_single_panel()
        else:
            self._activate_none_panel()

    def update_xy_entrys(self):
        if len(self.master.selected_items) != 1 or self.entry_x1 is None:
            return
        try:
            if not self.entry_x1.winfo_exists():
                return
        except Exception:
            return
        item_id = self.master.id_selected_item
        if self.is_segment:
            seg_ids = self.master.drawing_store.segment_canvas_ids(
                self.segment_obj.object_id) if self.segment_obj else []
            item_id = seg_ids[0] if seg_ids else None
        if item_id:
            z = self.master.zoom
            coords = [int(round(c / z)) for c in self.master.canvas.coords(item_id)]
            if len(coords) == 2:
                x1, y1 = coords
                x2, y2 = None, None
            elif len(coords) == 4:
                x1, y1, x2, y2 = coords
            else:
                return

            type_id = self.master.canvas.type(item_id)
            if type_id in ['text', 'image']:
                self.entry_x1.set(x1)
                self.entry_y1.set(y1)
            else:
                self.entry_x1.set(x1)
                self.entry_y1.set(y1)
                self.entry_x2.set(x2)
                self.entry_y2.set(y2)

    def update_item(self, *args):
        item_id = self.master.id_selected_item

        if self.master.canvas.type(item_id) == 'text':
            if self.is_segment and self.segment_obj:
                seg = self.segment_obj
                seg.update_config(
                    seg.columns, seg.labels,
                    self.distance.get(), self.char_limit.get(),
                    self.font_family_combobox.get(),
                    int(self.font_size_combobox.get()),
                    self.font_style_combobox.get().lower(),
                    self.orientation.get(),
                )
                seg.anchor_x = str(int(self.entry_x1.get()))
                seg.anchor_y = str(int(self.entry_y1.get()))
                self.master._rebuild_segment_preview_lines(seg)
                self.master.rebuild_segment_lines(seg)
                self.segment_itens = self.master.drawing_store.segment_canvas_ids(seg.object_id)
            else:
                z = self.master.zoom
                if not self.is_counter:
                    self.master.canvas.itemconfig(item_id, text=self.entry_text.get())
                self.master.canvas.itemconfig(item_id,
                                              font=(self.font_family_combobox.get(),
                                                    self.master._zfont(self.font_size_combobox.get()),
                                                    self.font_style_combobox.get().lower()),
                                              angle=self.orientation.get())
                self.master.canvas.coords(item_id, self.master._zs(self.entry_x1.get()),
                                          self.master._zs(self.entry_y1.get()))

        elif self.master.canvas.type(item_id) == 'image':
            z = self.master.zoom
            proportion = int(self.entry_proportion.get())
            orientation = int(self.orientation.get())
            if proportion != self.last_proportion or orientation != self.last_orientation:
                img = change_proportion(self.master.canvas_dict_images[item_id][2],
                                        int(round(proportion * z)), orientation=orientation)
                img[3] = proportion
                img[4] = orientation
                self.master.canvas.itemconfig(item_id, image=img[1])
                self.master.canvas_dict_images[item_id] = img
                self.last_proportion = proportion
                self.last_orientation = orientation

            if self.is_barcode and self.barcode_obj:
                obj = self.barcode_obj
                if self.barcode_text_entry is not None:
                    new_text = self.barcode_text_entry.get().strip()
                    if new_text:
                        obj.placeholder = new_text
                if self.barcode_column is not None:
                    obj.file_column = self.barcode_column.get()
                if obj.barcode_kind in ('barcode', 'barcode39') and self.barcode_width is not None:
                    obj.barcode_width = self.barcode_width.get()
                    obj.barcode_height = self.barcode_height.get()
                obj.x, obj.y = self.entry_x1.get(), self.entry_y1.get()
                obj.proportion, obj.orientation = str(proportion), str(orientation)

                barcode_text = obj.placeholder.replace('_', ' ')
                w, h = obj.barcode_width, obj.barcode_height
                if obj.barcode_kind == 'barcode':
                    create_barcode(barcode_text, w, h)
                    img = get_image('temp/codigo_de_barras.png')
                elif obj.barcode_kind == 'barcode39':
                    create_barcode39(barcode_text, w, h)
                    img = get_image('temp/codigo_de_barras39.png')
                elif obj.barcode_kind == 'barcodeQR':
                    create_qrcode(barcode_text)
                    img = get_image('temp/qr_code.png')
                else:
                    create_datamatrix(barcode_text)
                    img = get_image('temp/dmtx.png')
                img = change_proportion(img[2], int(round(proportion * z)), orientation)
                img[3] = proportion
                img[4] = orientation
                self.master.canvas_dict_images[item_id] = img
                self.master.canvas.itemconfig(item_id, image=img[1])

            self.master.canvas.coords(item_id, self.master._zs(self.entry_x1.get()),
                                      self.master._zs(self.entry_y1.get()))

        elif self.master.canvas.type(item_id) in ['line', 'rectangle']:
            dash = self.combobox_dash.get()
            dash_values = {'Normal': '', 'Pequeno': '4', 'Grande': '40'}

            self.master.canvas.itemconfig(item_id,
                                          dash=dash_values[dash],
                                          width=self.combobox_width.get())
            self.master.canvas.coords(item_id, self.master._zs(self.entry_x1.get()),
                                      self.master._zs(self.entry_y1.get()),
                                      self.master._zs(self.entry_x2.get()),
                                      self.master._zs(self.entry_y2.get()))
        self.master.update_save_button()

    def save_img(self):
        item_id = self.master.id_selected_item
        path = asksaveasfilename(defaultextension=".png", filetypes=[("Arquivos Imagem", "*.png")],
                                 initialfile=f'Img_{datetime.today().strftime("%Y%m%d%H%M%S")}')

        img = self.master.canvas_dict_images[item_id][2]

        img.save(path)
        open_path(path)

    def rebuild_barcode(self, *args):
        if not (self.is_barcode and self.barcode_obj and self.barcode_text_entry is not None):
            return
        new_text = self.barcode_text_entry.get().strip()
        if not new_text:
            return
        self.barcode_obj.placeholder = new_text
        self.update_item()

    def bring_to_front(self):
        self.master.canvas.lift(self.master.id_selected_item)

    def send_to_back(self):
        self.master.canvas.lower(self.master.id_selected_item)
        self.master.canvas.tag_lower('paper')


class GetImageWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

        self.geometry(calculate_center_screen_with_monitor(master, 250, 150, get_monitor(master)))
        self.minsize(250, 150)
        self.maxsize(250, 150)
        self.resizable(False, False)
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y
        self.filepath = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.btn_select_image = ctk.CTkButton(self, text='Selecione um arquivo', command=self.select_file)
        self.btn_select_image.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky='S')

        self.lbl_image_name = ctk.CTkLabel(self, text='')
        self.lbl_image_name.grid(row=1, column=0, columnspan=2, padx=10, sticky='N')

        self.btn_ok = ctk.CTkButton(self, text="OK", width=80, state="disabled", command=self.draw_image)
        self.btn_ok.grid(row=2, column=0, pady=10)

        self.btn_cancelar = ctk.CTkButton(self, width=80, text="Cancelar", fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED)
        self.btn_cancelar.grid(row=2, column=1, pady=10)

    def select_file(self):
        self.filepath = askopenfilename(filetypes=[("Image files", ["*.png", "*.jpg"])])
        self.lbl_image_name.configure(text=os.path.basename(self.filepath))
        if self.filepath:
            self.btn_ok.configure(state="normal")

    def draw_image(self):
        img = get_image(self.filepath)
        obj = make_image_object(int(round(self.master._zl(self.x))), int(round(self.master._zl(self.y))))
        disp = change_proportion(img[2], int(round(100 * self.master.zoom)))
        disp[3] = 100
        img_id = self.master.canvas.create_image(
            self.x, self.y, image=disp[0], anchor='sw', tags=obj.canvas_tags(),
        )
        self.master.canvas_dict_images[img_id] = disp
        self.master.register_new_canvas_item(img_id, obj)
        self.master.refresh()
        self.master.properties_window.refresh()
        self.destroy()


class GetTextWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

        self.geometry(calculate_center_screen_with_monitor(master, 420, 300, get_monitor(master)))
        self.minsize(420, 300)
        self.maxsize(420, 300)
        self.resizable(False, False)
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Fonte:').grid(row=0, column=0, pady=10, padx=10)
        self.font_list = ctk.CTkComboBox(self, values=FONT_LIST)
        self.font_list.grid(row=0, column=1, pady=10, padx=10, sticky='W')

        ctk.CTkLabel(self, text='Tamanho:').grid(row=1, column=0, pady=10, padx=10)
        self.fontsize = ctk.CTkComboBox(self, values=list(map(str, range(6, 28))))
        self.fontsize.set('10')
        self.fontsize.grid(row=1, column=1, pady=10, padx=10, sticky='W')

        ctk.CTkLabel(self, text='Orientação:').grid(row=2, column=0, pady=10, padx=10)
        self.orientation = ctk.CTkComboBox(self, values=['0', '90', '180', '270'])
        self.orientation.grid(row=2, column=1, pady=10, padx=10, sticky='W')

        self.counter_var = ctk.IntVar()
        self.counter = ctk.CTkCheckBox(self, text='Counter', command=self.verify_counter, variable=self.counter_var)
        self.counter.grid(row=3, column=0, padx=30, sticky='E')

        self.bold = ctk.CTkCheckBox(self, text='Bold')
        self.bold.grid(row=3, column=1, padx=10)

        ctk.CTkLabel(self, text='Texto').grid(row=4, column=0, columnspan=2, padx=10)
        self.text = ctk.CTkEntry(self, width=300)
        self.text.grid(row=5, column=0, columnspan=2, padx=10)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, command=self.draw_text)
        self.btn_ok.grid(row=6, column=0, pady=20, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED, command=self.destroy)
        self.btn_cancelar.grid(row=6, column=1, pady=20, padx=20)

    def draw_text(self):
        weight = "bold" if self.bold.get() else "normal"
        fonte = (self.font_list.get(), self.fontsize.get(), weight)
        if self.text.get().strip() == "":
            PopUpWindow(self, "Erro!", "O campo TEXTO não pode estar vazio")
        else:
            obj = make_text_object(
                int(round(self.master._zl(self.x))), int(round(self.master._zl(self.y))),
                self.text.get(), fonte[0], fonte[1], fonte[2],
                self.orientation.get(), is_counter=bool(self.counter_var.get()),
            )
            obj.scope = self.master._active_editor_scope()
            self.master.drawing_store.register(obj)
            self.master._render_object(obj)
            self.master.reset_all()
            self.destroy()

    def verify_counter(self):
        if self.counter_var.get():
            self.text.delete('0', 'end')
            self.text.insert('0', '0000001')
            self.text.configure(state='disabled')
        else:
            self.text.configure(state='normal')
            self.text.delete('0', 'end')


class GetBarcodeWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)

        self.geometry(calculate_center_screen_with_monitor(master, 380, 540, get_monitor(master)))
        self.minsize(380, 540)
        self.maxsize(380, 540)
        self.resizable(False, False)
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y

        self.title("Código de Barras")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text='Modelo:').grid(row=0, column=0, padx=10, pady=10, sticky='E')

        barcode_models = ['Barcode 128', 'Barcode 39', 'QRCode', 'Matrix']
        self.entry_model = ctk.CTkComboBox(self, values=barcode_models, width=120, command=self.enable_disable_config)
        self.entry_model.grid(row=0, column=1, padx=10, pady=10, sticky='W')

        ctk.CTkLabel(self, text='Espessura:').grid(row=1, column=0, padx=10, pady=10, sticky='E')

        barcode_widths = ['0.17', '0.18', '0.19', '0.20']
        self.entry_width = ctk.CTkComboBox(self, values=barcode_widths, width=120)
        self.entry_width.grid(row=1, column=1, padx=10, pady=10, sticky='W')

        ctk.CTkLabel(self, text='Altura:').grid(row=2, column=0, padx=10, pady=10, sticky='E')

        barcode_heights = ['1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '1.8', '1.9',
                           '2.0', '2.1', '2.2', '2.3', '2.4', '2.5', '2.6', '2.7', '2.8',
                           '2.9']

        self.entry_height = ctk.CTkComboBox(self, values=barcode_heights, width=120)
        self.entry_height.set('5')
        self.entry_height.grid(row=2, column=1, padx=10, pady=10, sticky='W')

        ctk.CTkLabel(self, text='Texto (Placeholder)').grid(row=3, column=0, columnspan=2, padx=10)

        self.text = ctk.CTkEntry(self, width=200)
        self.text.insert(0, 'FS123456789BR')
        self.text.grid(row=4, column=0, columnspan=2, padx=10)

        help_text = 'Selecione a coluna  do arquivo a ser usada no texto variavel'
        ctk.CTkLabel(self, text=help_text).grid(row=5, column=0, columnspan=2, pady=5)

        self.fields = ListBox(self, [f'Coluna_{i}' for i in range(1, 100)])
        self.fields.grid(row=6, column=0, columnspan=2)

        self.btn_ok = ctk.CTkButton(self, text="OK", width=120, state='disabled', command=self.create_barcode)
        self.btn_ok.grid(row=7, column=0, pady=20, padx=20)

        self.btn_cancelar = ctk.CTkButton(self, width=120, text="Cancelar", fg_color=BTN_RED,
                                          hover_color=BTN_HOVER_RED, command=self.destroy)
        self.btn_cancelar.grid(row=7, column=1, pady=20, padx=20)

    def create_barcode(self):
        if self.text.get():
            w, h, f = self.entry_width.get(), self.entry_height.get(), self.fields.radio_var.get()
            text = self.text.get()
            model_map = {
                'Barcode 128': 'barcode',
                'Barcode 39': 'barcode39',
                'QRCode': 'barcodeQR',
                'Matrix': 'barcodeMatrix',
            }
            kind = model_map[self.entry_model.get()]
            obj = make_barcode_object(
                kind, int(round(self.master._zl(self.x))), int(round(self.master._zl(self.y))),
                f, text, w, h,
            )
            obj.scope = self.master._active_editor_scope()
            self.master.drawing_store.register(obj)
            self.master._render_barcode(obj, companion_text=False)
            self.master.properties_window.refresh()
            self.destroy()
        else:
            PopUpWindow(self, 'Erro', 'Placeholder deve ser preenchido')

    def enable_disable_config(self, *args):
        if self.entry_model.get() in ['Barcode 128', 'Barcode 39']:
            self.entry_width.configure(state="normal")
            self.entry_height.configure(state="normal")
        else:
            self.entry_width.configure(state="disabled")
            self.entry_height.configure(state="disabled")

    def refresh(self, *args):
        self.btn_ok.configure(state='normal')


class GetSegmentWindow(ctk.CTkToplevel):
    def __init__(self, master, x, y, edit_segment=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iconbitmap(ICON)
        self.edit_segment = edit_segment

        self.geometry(calculate_center_screen_with_monitor(master, 600, 350, get_monitor(master)))
        self.minsize(600, 350)
        self.maxsize(600, 350)
        self.resizable(False, False)
        self.title('Editar Segmento' if edit_segment else 'Configurar Segmento')
        self.master = master
        self.grab_set()
        self.x = x
        self.y = y

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)
        self.grid_columnconfigure(3, weight=2)

        self.validation = self.register(self.is_valid_input)
        self.list = []
        self.checkbox_list = {}
        self.placeholders_list = []
        # ------------------ Fields Frame -----------------------------------------------
        self.fields_frame = ctk.CTkScrollableFrame(self, label_text='Selecionar campos do arquivo',
                                                   width=100, height=220)
        self.fields_frame.grid(padx=15, pady=15, row=0, column=0, rowspan=4)

        for i in range(1, 100):
            checkbox = ctk.CTkCheckBox(self.fields_frame, text=f'Coluna_{i}', border_width=1, corner_radius=3,
                                       checkbox_height=20, checkbox_width=20, border_color='white')
            checkbox.configure(command=lambda z=checkbox: self.update_placeholder_frame(z))

            checkbox.grid(padx=2, pady=5)
            self.checkbox_list[i] = checkbox

        # ------------------ Placeholders Frame -----------------------------------------
        self.placeholders_frame = None

        # ------------------ First Row (Labels and Input) -------------------------------
        ctk.CTkLabel(self, text='Placeholders', font=(FONT_LIST[0], 20, 'bold')).grid(row=0, column=1, sticky='W')

        ctk.CTkLabel(self, text='Limite caracteres:').grid(row=0, column=2, padx=5, sticky='E')

        self.input_largura = ctk.CTkEntry(self, width=50, height=10, fg_color='white', text_color='black',
                                          border_width=1, corner_radius=0, validate='key',
                                          validatecommand=(self.validation, '%S'))

        self.input_largura.grid(row=0, column=3, sticky='W')
        self.input_largura.insert(0, '0')

        # ------------------ Line Height ----------------------------------------------
        ctk.CTkLabel(self, text='Distância linhas:').grid(row=3, column=1, sticky='W')
        self.input_distancia = ctk.CTkEntry(self, width=50, height=10, fg_color='white', text_color='black',
                                            border_width=1, corner_radius=0, validate='key',
                                            validatecommand=(self.validation, '%S'))

        self.input_distancia.grid(row=3, column=1, sticky='E')
        self.input_distancia.insert(0, '15')

        # ------------------ Ok Button ------------------------------------------------
        self.btn_ok = ctk.CTkButton(self, text="OK", width=80, command=self.place_segment)
        self.btn_ok.grid(row=3, column=2, columnspan=2, sticky='E', padx=25)

        # ---------------- Font Properties -------------------------------------------
        ctk.CTkLabel(self, text='Fonte:').grid(padx=20, row=4, column=0, sticky='W')
        self.font = ctk.CTkComboBox(self, width=100, height=20, fg_color='white', text_color='black',
                                    border_width=1, corner_radius=0, values=FONT_LIST)
        self.font.grid(padx=20, row=4, column=0)

        ctk.CTkLabel(self, text='Tamanho:').grid(row=4, column=1, sticky='W')
        self.size = ctk.CTkComboBox(self, width=70, height=20, fg_color='white', text_color='black',
                                    border_width=1, corner_radius=0, values=[str(i) for i in range(6, 20)])
        self.size.set('10')
        self.size.grid(padx=20, row=4, column=1, sticky='E')

        self.bold = ctk.CTkCheckBox(self, checkbox_width=20, checkbox_height=20,
                                    corner_radius=0, text='Bold', border_width=2)
        self.bold.grid(row=4, column=2, sticky='W')

        if self.edit_segment:
            self._prefill_from_segment(self.edit_segment)
        else:
            self.no_selection_lbl()

    def _prefill_from_segment(self, seg: SegmentObject):
        self.input_largura.delete(0, 'end')
        self.input_largura.insert(0, seg.char_limit)
        self.input_distancia.delete(0, 'end')
        self.input_distancia.insert(0, seg.line_distance)
        self.font.set(seg.font_name)
        self.size.set(seg.font_size)
        if seg.font_style.lower() == 'bold':
            self.bold.select()
        self.list = list(seg.columns)
        for col in seg.columns:
            num = col.replace('Coluna_', '')
            if num.isdigit() and int(num) in self.checkbox_list:
                self.checkbox_list[int(num)].select()
        if self.placeholders_frame is not None:
            self.placeholders_frame.destroy()
        self.placeholders_frame = ctk.CTkScrollableFrame(self, width=320, height=210)
        self.placeholders_frame.grid(row=1, column=1, columnspan=3, rowspan=2, sticky='W')
        self.placeholders_list = []
        for i, col in enumerate(seg.columns):
            ctk.CTkLabel(self.placeholders_frame, text=col).grid(padx=10, row=i, column=0)
            entry = ctk.CTkEntry(self.placeholders_frame, width=230, height=10,
                                 fg_color='white', text_color='black',
                                 border_width=1, corner_radius=0)
            label = seg.labels[i] if i < len(seg.labels) else f'Placeholder {i}'
            entry.insert(0, label)
            entry.grid(column=1, row=i, sticky='W')
            self.placeholders_list.append(entry)

    def place_segment(self):
        if not self.placeholders_list:
            PopUpWindow(self, 'Erro', 'Selecione ao menos uma coluna')
            return
        char_limit = self.input_largura.get()
        columns = self.get_selected_checkbox().split('.') if self.get_selected_checkbox() else []
        labels = [entry.get() for entry in self.placeholders_list]
        font_style = 'bold' if self.bold.get() else 'normal'

        if self.edit_segment:
            seg = self.edit_segment
            seg.update_config(
                columns, labels, self.input_distancia.get(), char_limit,
                self.font.get(), self.size.get(), font_style, seg.orientation,
            )
            seg.anchor_x, seg.anchor_y = str(self.x), str(self.y)
            self.master._rebuild_segment_preview_lines(seg)
            self.master.rebuild_segment_lines(seg)
        else:
            seg = SegmentObject(
                object_id=new_object_id('seg-'),
                scope=self.master._active_editor_scope(),
                columns=columns,
                labels=labels,
                line_distance=str(self.input_distancia.get()),
                char_limit=str(char_limit),
                font_name=self.font.get(),
                font_size=str(self.size.get()),
                font_style=font_style,
                orientation='0',
                anchor_x=str(self.x),
                anchor_y=str(self.y),
            )
            self.master.drawing_store.register(seg)
            self.master._rebuild_segment_preview_lines(seg)
            self.master._render_segment(seg)
            new_ids = self.master.drawing_store.segment_canvas_ids(seg.object_id)
            self.master.id_selected_item = new_ids[0] if new_ids else None
            self.master.properties_window.last_id = None

        self.master.refresh()
        self.master.properties_window.refresh()
        self.destroy()

    def get_selected_checkbox(self):
        selected_checkbox = [i.cget('text') for i in self.checkbox_list.values() if i.get()]
        return '.'.join(self.list)

    def update_placeholder_frame(self, widget):
        placeholders_content = [entry.get() for entry in self.placeholders_list]
        placeholders_content = dict(enumerate(placeholders_content))
        if widget.get():
            self.list.append(widget.cget('text'))
        else:
            self.list.remove(widget.cget('text'))

        if self.placeholders_frame is not None:
            self.placeholders_frame.destroy()
        self.placeholders_frame = ctk.CTkScrollableFrame(self, width=320, height=210)
        self.placeholders_frame.grid(row=1, column=1, columnspan=3, rowspan=2, sticky='W')
        self.placeholders_frame.columnconfigure(0, weight=1)
        self.placeholders_frame.columnconfigure(1, weight=3)

        self.placeholders_list = []
        for i, checkbox in enumerate(self.list):
            ctk.CTkLabel(self.placeholders_frame, text=checkbox).grid(padx=10, row=i, column=0)
            entry = ctk.CTkEntry(self.placeholders_frame, width=230, height=10,
                                 fg_color='white', text_color='black',
                                 border_width=1, corner_radius=0)
            self.placeholders_list.append(entry)
            entry.insert(0, placeholders_content.get(i, f'Placeholder {i}'))
            entry.grid(column=1, row=i, sticky='W')

        if not self.list:
            self.no_selection_lbl()

    def no_selection_lbl(self):
        self.placeholders_frame = ctk.CTkScrollableFrame(self, width=320, height=210)
        self.placeholders_frame.grid(row=1, column=1, columnspan=3, rowspan=2, sticky='W')
        self.placeholders_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(self.placeholders_frame, text='SELECIONE UM CAMPO', font=(FONT_LIST[0], 25, 'bold'),
                     text_color='#161616', height=180).grid(row=0, column=0)

    @staticmethod
    def is_valid_input(input_str):
        return input_str.isdigit() or input_str == ""


