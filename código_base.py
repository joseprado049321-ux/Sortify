# Ensure os.path.expandvars is imported
from os.path import expandvars

# Ensure USER_FOLDERS is defined at the top of the file
USER_FOLDERS = {
    "Documentos": expandvars("%USERPROFILE%\\Documents"),
    "Audio": expandvars("%USERPROFILE%\\Music"),
    "Videos": expandvars("%USERPROFILE%\\Videos"),
    "Imágenes": expandvars("%USERPROFILE%\\Pictures"),
    "Otros": expandvars("%USERPROFILE%\\Downloads"),
}

import os
import re
import time
import shutil
import string
import hashlib
import ctypes
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT = "Inter"

REGLAS = {
    "Imágenes": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".raw", ".cr2", ".svg", ".bmp", ".tiff", ".tif", ".heic", ".ico", ".avif", ".psd"],
    "Documentos": [".pdf", ".docx", ".txt", ".xlsx", ".pptx", ".csv", ".doc", ".xls", ".ppt", ".odt", ".ods", ".odp", ".rtf", ".md", ".json", ".xml"],
    "Videos": [".mp4", ".mkv", ".mov", ".avi", ".flv", ".webm", ".wmv", ".mpeg", ".mpg", ".3gp", ".m4v", ".ts"],
    "Audio": [".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma", ".aiff", ".mid", ".midi"],
    "Libros": [".epub", ".mobi", ".azw3", ".pb2", ".cbz", ".cbr"],
    "Instaladores": [".exe", ".msi", ".dmg", ".pkg", ".apk", ".deb", ".rpm", ".appimage", ".bat", ".sh"],
    "Comprimidos": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab", ".tgz"],
    "ISOs y Discos": [".iso", ".vmdk", ".img", ".bin", ".cue", ".nrg", ".qcow2", ".vdi", ".dmg"],
    "Código": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".php"],
    "Fuentes": [".ttf", ".otf", ".woff"],
    "Subtítulos": [".srt", ".ass", ".vtt"],
    "Torrents": [".torrent"],
    "Bases de Datos": [".db", ".sqlite", ".sql"]
}

# Patrón para detectar nombres de archivo que son copias
PATRON_COPIA = re.compile(
    r'(\s*[-–]?\s*(copy|copia|kopie|copie|cópia)\s*(\(\d+\))?'
    r'|\s*[-–]?\s*\(\d+\))\s*$',
    re.IGNORECASE
)


# ── Instalador PhotoRec (módulo, sin cambios de versión anterior) ──────────

def instalar_photorec_automatico(callback=None):
    carpeta_motor = os.path.join(os.getcwd(), "motor")
    os.makedirs(carpeta_motor, exist_ok=True)
    ruta_zip = os.path.join(carpeta_motor, "testdisk.zip")
    exe_path = os.path.join(carpeta_motor, "testdisk-7.2", "photorec_win.exe")

    if os.path.exists(exe_path):
        if callback:
            callback("ya_instalado", exe_path)
        return True

    try:
        if callback:
            callback("descargando", None)
        urllib.request.urlretrieve(
            "https://www.cgsecurity.org/testdisk-7.2.win64.zip", ruta_zip)

        if callback:
            callback("extrayendo", None)
        with zipfile.ZipFile(ruta_zip, 'r') as z:
            z.extractall(carpeta_motor)
        os.remove(ruta_zip)

        if callback:
            callback("listo", exe_path)
        return True

    except Exception as e:
        if callback:
            callback("error", str(e))
        return False


class SortifyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.title("Sortify // Organizador Inteligente")
        self.resizable(False, False)

        # Fuentes
        self.f_titulo    = ctk.CTkFont(family=FONT, size=32, weight="bold")
        self.f_subtitulo = ctk.CTkFont(family=FONT, size=14, slant="italic")
        self.f_btn_lg    = ctk.CTkFont(family=FONT, size=15, weight="bold")
        self.f_btn_sm    = ctk.CTkFont(family=FONT, size=13, weight="bold")
        self.f_label     = ctk.CTkFont(family=FONT, size=11)
        self.f_body      = ctk.CTkFont(family=FONT, size=13)
        self.f_progreso  = ctk.CTkFont(family=FONT, size=14)
        self.f_exito     = ctk.CTkFont(family=FONT, size=22, weight="bold")
        self.f_toast     = ctk.CTkFont(family=FONT, size=13)

        self.BTN_STYLE    = dict(width=250, height=50, corner_radius=15, font=self.f_btn_lg)
        self.BTN_SM_STYLE = dict(width=220, height=38, corner_radius=15, font=self.f_btn_sm)

        # Estado: organizar
        self.ruta_seleccionada = ""
        self.historial = []
        self._toast_after_id = None
        self.var_eliminar_duplicados = ctk.BooleanVar(value=False)

        # Estado: PhotoRec
        self.photorec_output_dir   = ""
        self.photorec_disco        = ""
        self.photorec_cancelado    = False
        self._photorec_animando    = False
        self._photorec_anim_val    = 0.0
        self._photorec_anim_dir    = 1

        # Add new variables for the checkboxes
        self.var_organize_on_completion = ctk.BooleanVar(value=False)
        self.var_scan_subfolders = ctk.BooleanVar(value=False)
        self.var_save_in_same_folder = ctk.BooleanVar(value=False)

        # Construir frames
        self._build_frame_inicial()
        self._build_frame_resumen()
        self._build_frame_progreso()
        self._build_frame_resultado()
        self._build_frame_photorec()
        self._build_frame_photorec_config()
        self._build_frame_photorec_progreso()
        self._build_frame_photorec_resultado()

        self._mostrar(self.frame_inicial, "500x350")

    # ── helpers ────────────────────────────────────────────────────────────

    def _mostrar(self, frame, geometry="500x350"):
        for f in (self.frame_inicial, self.frame_resumen,
                  self.frame_progreso, self.frame_resultado,
                  self.frame_photorec, self.frame_photorec_config,
                  self.frame_photorec_progreso, self.frame_photorec_resultado):
            f.place_forget()
        self.geometry(geometry)
        frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _btn(self, parent, text, command, small=False, **kw):
        base = self.BTN_SM_STYLE if small else self.BTN_STYLE
        return ctk.CTkButton(parent, text=text, command=command, **{**base, **kw})

    # ── Frame 1: Inicial ───────────────────────────────────────────────────

    def _build_frame_inicial(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_inicial = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(50, 0))
        ctk.CTkLabel(f, text="Ordena tus archivos en un clic.",
                     font=self.f_subtitulo).pack(pady=(10, 40))
        self._btn(f, "📁  Organizar Archivos",
                  self._seleccionar_carpeta).pack(pady=(0, 12))
        self._btn(f, "🛠  Recuperar Archivos",
                  self._abrir_photorec).pack()

    # ── Frame 2: Resumen ───────────────────────────────────────────────────

    def _build_frame_resumen(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_resumen = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(22, 0))

        self.lbl_ruta = ctk.CTkLabel(f, text="", text_color="#1f6aa5",
                                     font=self.f_label, wraplength=450,
                                     cursor="hand2")
        self.lbl_ruta.pack(pady=(4, 8))
        self.lbl_ruta.bind("<Button-1>", lambda e: self._seleccionar_carpeta())

        self.txt_resumen = ctk.CTkTextbox(f, width=440, height=130,
                                          corner_radius=10, state="disabled",
                                          font=self.f_body)
        self.txt_resumen.pack(padx=20)

        # ── NUEVO: checkbox duplicados ─────────────────────────────────────
        self.chk_duplicados = ctk.CTkCheckBox(
            f,
            text="  Eliminar duplicados al organizar",
            variable=self.var_eliminar_duplicados,
            font=self.f_body,
            checkbox_width=20, checkbox_height=20
        )
        self.chk_duplicados.pack(pady=(10, 0), anchor="w", padx=36)

        self.chk_organize_on_completion = ctk.CTkCheckBox(
            f,
            text="  Organizar archivos al finalizar",
            variable=self.var_organize_on_completion,
            font=self.f_body,
            checkbox_width=20, checkbox_height=20
        )
        self.chk_organize_on_completion.pack(pady=(10, 0), anchor="w", padx=36)

        self.chk_scan_subfolders = ctk.CTkCheckBox(
            f,
            text="  Escanear subcarpetas",
            variable=self.var_scan_subfolders,
            font=self.f_body,
            checkbox_width=20, checkbox_height=20
        )
        self.chk_scan_subfolders.pack(pady=(10, 0), anchor="w", padx=36)

        self.chk_save_in_same_folder = ctk.CTkCheckBox(
            f,
            text="  Guardar en la misma carpeta",
            variable=self.var_save_in_same_folder,
            font=self.f_body,
            checkbox_width=20, checkbox_height=20
        )
        self.chk_save_in_same_folder.pack(pady=(10, 0), anchor="w", padx=36)

        self._btn(f, "Organizar Carpeta", self._ejecutar_organizacion,
                  height=45).pack(pady=(12, 0))
        self._btn(f, "Volver al menú principal", self._volver_inicio,
                  small=True).pack(pady=(12, 0))

    # ── Frame 3: Progreso organización ─────────────────────────────────────

    def _build_frame_progreso(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_progreso = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(70, 0))

        self.lbl_progreso = ctk.CTkLabel(f, text="Moviendo 0/0 archivos",
                                         font=self.f_progreso)
        self.lbl_progreso.pack(pady=(30, 8))

        self.barra = ctk.CTkProgressBar(f, width=400)
        self.barra.set(0)
        self.barra.pack()

    # ── Frame 4: Resultado organización ────────────────────────────────────

    def _build_frame_resultado(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_resultado = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(40, 0))
        ctk.CTkLabel(f, text="¡Archivos Movidos!", font=self.f_exito,
                     text_color="#2ecc71").pack(pady=(14, 24))

        self._btn(f, "Deshacer Cambios", self._deshacer).pack(pady=(0, 8))
        self._btn(f, "Volver al menú principal", self._volver_inicio).pack()

        self.toast = ctk.CTkLabel(
            f, text="Se han revertido los cambios",
            fg_color="#1a1a1a", corner_radius=8,
            font=self.f_toast, text_color="white", padx=18, pady=8
        )

    # ── Frame 5: PhotoRec — intro / instalación ────────────────────────────

    def _build_frame_photorec(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_photorec = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(50, 0))
        ctk.CTkLabel(f, text="Recuperación de Archivos", font=self.f_exito,
                     text_color="#1abc9c").pack(pady=(10, 4))
        ctk.CTkLabel(f, text="Descarga el motor PhotoRec para recuperar archivos borrados.",
                     font=self.f_subtitulo, wraplength=400).pack(pady=(0, 18))

        self.lbl_photorec_estado = ctk.CTkLabel(
            f, text="Listo para instalar el motor de recuperación.", font=self.f_body)
        self.lbl_photorec_estado.pack(pady=(0, 18))

        self.btn_photorec_instalar = self._btn(
            f, "⬇  Instalar motor y continuar", self._instalar_y_continuar)
        self.btn_photorec_instalar.pack(pady=(0, 10))
        self._btn(f, "Volver al menú principal", self._volver_inicio,
                  small=True).pack()

    # ── Frame 6: PhotoRec — configuración ──────────────────────────────────

    def _build_frame_photorec_config(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_photorec_config = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(22, 0))
        ctk.CTkLabel(f, text="Configurar Recuperación", font=self.f_exito,
                     text_color="#1abc9c").pack(pady=(8, 16))

        # Selector de disco
        ctk.CTkLabel(f, text="Disco a analizar:", font=self.f_body,
                     anchor="w").pack(anchor="w", padx=36)
        self.combo_disco = ctk.CTkComboBox(
            f, width=428, values=[], state="readonly", font=self.f_body)
        self.combo_disco.pack(padx=36, pady=(4, 14))

        # Carpeta de destino
        ctk.CTkLabel(f, text="Carpeta donde guardar los archivos recuperados:",
                     font=self.f_body, anchor="w").pack(anchor="w", padx=36)

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=36, pady=(4, 18))
        self.lbl_output_dir = ctk.CTkLabel(
            row, text="(ninguna seleccionada)",
            font=self.f_label, text_color="gray",
            anchor="w", wraplength=350)
        self.lbl_output_dir.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="📂", width=46, height=32,
                      command=self._seleccionar_output_dir).pack(side="right")

        self._btn(f, "▶  Iniciar Recuperación",
                  self._iniciar_recuperacion).pack(pady=(0, 10))
        self._btn(f, "Volver al menú principal", self._volver_inicio,
                  small=True).pack()

    # ── Frame 7: PhotoRec — progreso ───────────────────────────────────────

    def _build_frame_photorec_progreso(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_photorec_progreso = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(55, 0))
        ctk.CTkLabel(f, text="Recuperando archivos en segundo plano…",
                     font=self.f_subtitulo).pack(pady=(6, 0))

        self.lbl_photorec_count = ctk.CTkLabel(
            f, text="0 archivos recuperados hasta ahora…", font=self.f_progreso)
        self.lbl_photorec_count.pack(pady=(26, 8))

        self.barra_photorec = ctk.CTkProgressBar(f, width=400)
        self.barra_photorec.set(0)
        self.barra_photorec.pack()

        ctk.CTkLabel(
            f,
            text="PhotoRec corre minimizado en la barra de tareas.\n"
                 "Sortify detecta automáticamente cuando termina.",
            font=self.f_label, text_color="gray", justify="center"
        ).pack(pady=(14, 0))

        self._btn(f, "⏹  Detener recuperación",
                  self._cancelar_recuperacion,
                  small=True,
                  fg_color="#c0392b", hover_color="#922b21").pack(pady=(18, 0))

    # ── Frame 8: PhotoRec — resultado ──────────────────────────────────────

    def _build_frame_photorec_resultado(self):
        f = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_photorec_resultado = f

        ctk.CTkLabel(f, text="Sortify", font=self.f_titulo).pack(pady=(40, 0))
        ctk.CTkLabel(f, text="¡Recuperación Completada!", font=self.f_exito,
                     text_color="#2ecc71").pack(pady=(14, 8))

        self.lbl_photorec_resultado = ctk.CTkLabel(
            f, text="0 archivos recuperados", font=self.f_progreso)
        self.lbl_photorec_resultado.pack(pady=(0, 26))

        self._btn(f, "📂  Abrir Carpeta de Recuperación",
                  self._abrir_carpeta_recuperacion).pack(pady=(0, 10))
        self._btn(f, "Volver al menú principal", self._volver_inicio).pack()

    # ── Lógica original: organizar ─────────────────────────────────────────

    def _seleccionar_carpeta(self):
        ruta = filedialog.askdirectory()
        if not ruta:
            return
        self.ruta_seleccionada = ruta
        self._poblar_resumen(ruta)
        self._mostrar(self.frame_resumen, "500x430")

    def _poblar_resumen(self, ruta):
        archivos = []

        if self.var_scan_subfolders.get():
            for root, dirs, files in os.walk(ruta):
                for file in files:
                    archivos.append(os.path.join(root, file))
        else:
            for file in os.listdir(ruta):
                full_path = os.path.join(ruta, file)
                if os.path.isfile(full_path):
                    archivos.append(full_path)

        conteo = {}
        for archivo in archivos:
            ext = Path(archivo).suffix.lower()
            cat = "Otros"
            for nombre, exts in REGLAS.items():
                if ext in exts:
                    cat = nombre
                    break
            conteo[cat] = conteo.get(cat, 0) + 1

        n = len(archivos)
        lineas = [f"📁  Total: {n} archivo{'s' if n != 1 else ''} encontrado{'s' if n != 1 else ''}\n"]
        if conteo:
            for cat in sorted(conteo):
                c = conteo[cat]
                lineas.append(f"   • {cat}: {c} archivo{'s' if c != 1 else ''}")
        else:
            lineas.append("   (carpeta vacía)")

        self.lbl_ruta.configure(text=f"📂  {ruta}  ✎")
        self.txt_resumen.configure(state="normal")
        self.txt_resumen.delete("1.0", "end")
        self.txt_resumen.insert("1.0", "\n".join(lineas))
        self.txt_resumen.configure(state="disabled")

    def _ejecutar_organizacion(self):
        self.historial = []
        self.barra.set(0)
        self.lbl_progreso.configure(text="Moviendo 0/0 archivos")
        self._mostrar(self.frame_progreso, "500x300")
        threading.Thread(target=self._organizar_hilo, daemon=True).start()

    def _organizar_hilo(self):
        ruta = self.ruta_seleccionada
        archivos = []

        if self.var_scan_subfolders.get():
            for root, dirs, files in os.walk(ruta):
                for file in files:
                    archivos.append(os.path.join(root, file))
        else:
            for file in os.listdir(ruta):
                full_path = os.path.join(ruta, file)
                if os.path.isfile(full_path):
                    archivos.append(full_path)
        total = len(archivos)

        try:
            for i, archivo in enumerate(archivos):
                nombre_archivo = os.path.basename(archivo)
                ext = Path(nombre_archivo).suffix.lower()
                cat = "Otros"
                for nombre, exts in REGLAS.items():
                    if ext in exts:
                        cat = nombre
                        break

                if self.var_save_in_same_folder.get():
                    # Save in the same folder
                    carpeta_dest = os.path.join(ruta, cat)
                else:
                    # Save in default user folders
                    carpeta_dest = USER_FOLDERS.get(cat, USER_FOLDERS["Otros"])

                os.makedirs(carpeta_dest, exist_ok=True)

                origen = archivo
                destino = os.path.join(carpeta_dest, nombre_archivo)
                shutil.move(origen, destino)
                self.historial.append((destino, origen))

                actual = i + 1
                self.after(0, lambda a=actual, t=total: self._tick_progreso(a, t))

            # ── NUEVO: Eliminar duplicados si el checkbox está marcado ──────
            if self.var_eliminar_duplicados.get():
                self.after(0, lambda: self.lbl_progreso.configure(
                    text="Buscando y eliminando duplicados…"))
                self._eliminar_duplicados_tras_organizar(ruta)

            self.after(0, self._finalizar)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error",
                        f"No se pudo organizar:\n{e}"))

    def _tick_progreso(self, actual, total):
        self.lbl_progreso.configure(text=f"Moviendo {actual}/{total} archivos")
        self.barra.set(actual / total if total else 0)

    def _finalizar(self):
        self._mostrar(self.frame_resultado, "500x350")

    def _deshacer(self):
        try:
            for destino, origen in self.historial:
                if os.path.exists(destino):
                    shutil.move(destino, origen)

            for nombre in list(REGLAS.keys()) + ["Otros"]:
                carpeta = os.path.join(self.ruta_seleccionada, nombre)
                if os.path.isdir(carpeta) and not os.listdir(carpeta):
                    os.rmdir(carpeta)

            self.historial = []
            self._mostrar_toast()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo deshacer:\n{e}")

    def _mostrar_toast(self):
        if self._toast_after_id:
            self.after_cancel(self._toast_after_id)
        self.toast.place(relx=0.5, rely=0.92, anchor="center")
        self._toast_after_id = self.after(3000, self._ocultar_toast)

    def _ocultar_toast(self):
        self.toast.place_forget()
        self._toast_after_id = None

    def _volver_inicio(self):
        self.ruta_seleccionada = ""
        self.historial = []
        self._ocultar_toast()
        self._photorec_animando = False   # detener animación si estaba activa
        self._mostrar(self.frame_inicial, "500x350")

    # ── NUEVO: Lógica duplicados (integrada en organizar) ──────────────────

    def _hash_md5(self, filepath, chunk=65536):
        h = hashlib.md5()
        with open(filepath, "rb") as fh:
            while True:
                data = fh.read(chunk)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()

    def _limpiar_nombre_copia(self, nombre_con_ext):
        """Devuelve el nombre sin patrones de copia ('Copy', 'Copia', '(1)', etc.)."""
        p = Path(nombre_con_ext)
        stem = PATRON_COPIA.sub("", p.stem).strip()
        return stem + p.suffix

    def _elegir_mejor(self, a, b):
        """Devuelve (conservar, eliminar): prefiere el archivo sin patrón de copia."""
        a_es_copia = bool(PATRON_COPIA.search(Path(a).stem))
        b_es_copia = bool(PATRON_COPIA.search(Path(b).stem))
        if not a_es_copia and b_es_copia:
            return a, b
        if a_es_copia and not b_es_copia:
            return b, a
        return a, b  # ambos o ninguno: conservar el primero hallado

    def _eliminar_duplicados_tras_organizar(self, ruta_raiz):
        """
        Recorre las subcarpetas creadas, elimina archivos con contenido duplicado
        (por MD5) y, si el conservado tiene patrón de copia en el nombre, lo renombra.
        """
        hashes: dict[str, str] = {}   # md5 → ruta del archivo conservado

        for dirpath, _, filenames in os.walk(ruta_raiz):
            for fn in filenames:
                filepath = os.path.join(dirpath, fn)
                try:
                    h = self._hash_md5(filepath)
                except Exception:
                    continue

                if h in hashes:
                    conservar, eliminar = self._elegir_mejor(hashes[h], filepath)
                    try:
                        os.remove(eliminar)
                    except Exception:
                        pass
                    # Renombrar el conservado si su nombre tiene patrón de copia
                    nombre_actual = os.path.basename(conservar)
                    nombre_limpio = self._limpiar_nombre_copia(nombre_actual)
                    if nombre_limpio != nombre_actual:
                        nuevo_path = os.path.join(
                            os.path.dirname(conservar), nombre_limpio)
                        if not os.path.exists(nuevo_path):
                            try:
                                os.rename(conservar, nuevo_path)
                                conservar = nuevo_path
                            except Exception:
                                pass
                    hashes[h] = conservar
                else:
                    hashes[h] = filepath

    # ── NUEVO: Lógica PhotoRec ─────────────────────────────────────────────

    def _abrir_photorec(self):
        exe = os.path.join(os.getcwd(), "motor", "testdisk-7.2", "photorec_win.exe")
        if os.path.exists(exe):
            # Motor ya instalado → saltar directo a configuración
            self._cargar_config_photorec()
        else:
            self.lbl_photorec_estado.configure(
                text="Listo para instalar el motor de recuperación.")
            self.btn_photorec_instalar.configure(
                text="⬇  Instalar motor y continuar", state="normal")
            self._mostrar(self.frame_photorec, "500x380")

    def _instalar_y_continuar(self):
        self.btn_photorec_instalar.configure(state="disabled")
        self.lbl_photorec_estado.configure(text="⏳  Iniciando…")
        threading.Thread(target=self._photorec_instalar_hilo, daemon=True).start()

    def _photorec_instalar_hilo(self):
        MENSAJES = {
            "descargando":  "⏳  Descargando motor de recuperación…",
            "extrayendo":   "📦  Extrayendo archivos…",
            "ya_instalado": "✅  Motor ya instalado.",
            "listo":        "✅  ¡Instalación completada!",
        }

        def callback(estado, dato):
            if estado == "error":
                msg = f"❌  Error: {dato}"
                self.after(0, lambda m=msg:
                           self.lbl_photorec_estado.configure(text=m))
                self.after(0, lambda:
                           self.btn_photorec_instalar.configure(state="normal"))
                return
            msg = MENSAJES.get(estado, "")
            self.after(0, lambda m=msg:
                       self.lbl_photorec_estado.configure(text=m))
            if estado in ("listo", "ya_instalado"):
                self.after(700, self._cargar_config_photorec)

        instalar_photorec_automatico(callback=callback)

    def _cargar_config_photorec(self):
        """Puebla el combo de discos y muestra el frame de configuración."""
        discos = self._obtener_discos()
        self.combo_disco.configure(values=discos)
        if discos:
            self.combo_disco.set(discos[0])
        self.lbl_output_dir.configure(
            text="(ninguna seleccionada)", text_color="gray")
        self.photorec_output_dir = ""
        self._mostrar(self.frame_photorec_config, "500x410")

    def _obtener_discos(self):
        """Lista unidades lógicas disponibles con su tipo y nombre (Windows)."""
        drives = []
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            tipos = {2: "Extraíble", 3: "Disco local", 4: "Red", 5: "CD/DVD"}
            for letra in string.ascii_uppercase:
                if bitmask & 1:
                    ruta = f"{letra}:\\"
                    tipo = ctypes.windll.kernel32.GetDriveTypeW(ruta)
                    etiqueta = tipos.get(tipo, "")
                    nombre = ctypes.create_unicode_buffer(1024)
                    ctypes.windll.kernel32.GetVolumeInformationW(ruta, nombre, 1024, None, None, None, None, 0)
                    drives.append(f"{letra}: ({etiqueta}) - {nombre.value}" if etiqueta else f"{letra}:")
                bitmask >>= 1
        except Exception:
            drives = ["C:"]
        return drives or ["C:"]

    def _seleccionar_output_dir(self):
        ruta = filedialog.askdirectory(
            title="Selecciona dónde guardar los archivos recuperados")
        if ruta:
            self.photorec_output_dir = ruta
            self.lbl_output_dir.configure(
                text=f"📂  {ruta}", text_color="white")

    def _iniciar_recuperacion(self):
        if not self.photorec_output_dir:
            messagebox.showwarning("Falta carpeta de destino",
                "Por favor selecciona una carpeta de destino antes de continuar.")
            return

        self.photorec_disco = self.combo_disco.get().split()[0]
        exe = os.path.join(os.getcwd(), "motor", "testdisk-7.2", "photorec_win.exe")

        # Crear subcarpeta con timestamp dentro del directorio elegido.
        # Así PhotoRec siempre escribe en una carpeta nueva y no genera
        # "Recuperados.1", "Recuperados.2"... en ejecuciones sucesivas.
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        destino = os.path.join(self.photorec_output_dir, f"Sesion_{ts}")
        os.makedirs(destino, exist_ok=True)

        # Solo pasamos el directorio de destino; PhotoRec usa su propia UI
        # para elegir el disco (/cmd tiene problemas con paths de Windows en ShellExecuteW).
        params = f'/log /d "{destino}"'

        # SW_SHOWNORMAL (1): ventana visible — PhotoRec necesita su consola activa.
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1)

        if ret <= 32:
            messagebox.showerror("Error al iniciar PhotoRec",
                f"Código de error: {ret}\n"
                "Asegúrate de aceptar el control de cuentas de usuario (UAC).")
            return


        # Preparar y mostrar frame de progreso
        self.photorec_cancelado = False
        self._photorec_animando  = True
        self._photorec_anim_val  = 0.0
        self._photorec_anim_dir  = 1
        self.lbl_photorec_count.configure(
            text="0 archivos recuperados hasta ahora…")
        self.barra_photorec.set(0)
        self._mostrar(self.frame_photorec_progreso, "500x370")
        self._animar_barra_photorec()
        threading.Thread(target=self._monitorear_recuperacion, daemon=True).start()

    # ── Animación ping-pong de la barra ───────────────────────────────────

    def _animar_barra_photorec(self):
        if not self._photorec_animando:
            return
        self._photorec_anim_val += 0.025 * self._photorec_anim_dir
        if self._photorec_anim_val >= 1.0:
            self._photorec_anim_val = 1.0
            self._photorec_anim_dir = -1
        elif self._photorec_anim_val <= 0.0:
            self._photorec_anim_val = 0.0
            self._photorec_anim_dir = 1
        self.barra_photorec.set(self._photorec_anim_val)
        self.after(30, self._animar_barra_photorec)

    def _contar_archivos_recuperados(self):
        try:
            carpeta_base = self.photorec_output_dir

            if not carpeta_base or not os.path.isdir(carpeta_base):
                return 0

            total = 0

            # Examina TODAS las carpetas y subcarpetas
            for root, dirs, files in os.walk(carpeta_base):

                # DEBUG
                print(f"ESCANEANDO: {root} -> {len(files)}")

                total += len(files)

            print("TOTAL:", total)

            return total

        except Exception as e:
            print("ERROR CONTANDO:", e)
            return 0

    def _monitorear_recuperacion(self):
        """Hilo: sondea el proceso y el conteo de archivos hasta que termina."""
        time.sleep(1)   # dar tiempo al UAC y al arranque de PhotoRec

        ultimo_conteo = -1
        ticks_estable = 0   # cuántos ciclos seguidos sin cambio en el conteo

        while not self.photorec_cancelado:
            conteo    = self._contar_archivos_recuperados()

            self.after(0, lambda c=conteo: self.lbl_photorec_count.configure(
                text=f"{c} archivo{'s' if c != 1 else ''} "
                     f"recuperado{'s' if c != 1 else ''} hasta ahora…"
            ))

            if conteo != ultimo_conteo:
                ultimo_conteo = conteo
                ticks_estable = 0
            else:
                ticks_estable += 1

            # Terminar solo cuando: proceso muerto Y conteo sin cambios ≥10 s
            # Esto evita falsos negativos cuando tasklist no ve el proceso elevado
            # en algún ciclo puntual.
            if ticks_estable >= 30:
                break

            time.sleep(2)

        if not self.photorec_cancelado:
            conteo_final = self._contar_archivos_recuperados()
            self.after(0, lambda c=conteo_final: self._finalizar_recuperacion(c))

    def _cancelar_recuperacion(self):
        self.photorec_cancelado = True
        self._photorec_animando = False
        try:
            subprocess.run(
                ['taskkill', '/f', '/im', 'photorec_win.exe'],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass
        self._finalizar_recuperacion(self._contar_archivos_recuperados())

    def _finalizar_recuperacion(self, conteo):
        self._photorec_animando = False
        self.barra_photorec.set(1)
        if conteo > 0:
            txt = (f"✅  {conteo} archivo{'s' if conteo != 1 else ''} "
                   f"recuperado{'s' if conteo != 1 else ''}")
        else:
            txt = "No se encontraron archivos para recuperar."
        self.lbl_photorec_resultado.configure(text=txt)
        self._mostrar(self.frame_photorec_resultado, "500x370")

    def _abrir_carpeta_recuperacion(self):
        ruta = self.photorec_output_dir

        if ruta and os.path.isdir(ruta):
            os.startfile(ruta)


    def _cerrar_photorec(self):
        """Cierra PhotoRec si sigue abierto."""
        try:
            subprocess.run(
                ['taskkill', '/f', '/im', 'photorec_win.exe'],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass

    def on_closing(self):
        """Cerrar Sortify y también PhotoRec."""
        self.photorec_cancelado = True
        self._photorec_animando = False

        self._cerrar_photorec()

        self.destroy()

if __name__ == "__main__":
    app = SortifyApp()
    app.mainloop()