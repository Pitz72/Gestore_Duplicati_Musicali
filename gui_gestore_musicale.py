import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import threading
from pathlib import Path
from typing import List

# Importa le nuove funzioni di pianificazione ed esecuzione
from gestore_duplicati_musicali import (
    pianifica_gestione_completa,
    esegui_piano_azioni,
    SpostaFileAzione
)

class PreviewWindow(tk.Toplevel):
    """Finestra modale per visualizzare l'anteprima del piano di azioni."""
    def __init__(self, parent, piano: List[SpostaFileAzione], execute_callback):
        super().__init__(parent)
        self.transient(parent)
        self.title("Anteprima Spostamenti")
        self.geometry("900x500")
        self.parent = parent
        self.piano = piano
        self.execute_callback = execute_callback

        self.create_widgets()
        self.populate_tree()

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.grab_set()
        self.wait_window(self)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        # Treeview per mostrare il piano
        columns = ("sorgente", "destinazione", "motivazione")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")

        self.tree.heading("sorgente", text="File Originale")
        self.tree.heading("destinazione", text="Nuova Posizione")
        self.tree.heading("motivazione", text="Motivazione")

        self.tree.column("sorgente", width=350)
        self.tree.column("destinazione", width=350)
        self.tree.column("motivazione", width=150, anchor=tk.CENTER)

        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Frame per i pulsanti
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        ttk.Button(button_frame, text="Esegui Spostamenti", command=self.execute).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Annulla", command=self.cancel).pack(side=tk.RIGHT)

    def populate_tree(self):
        for azione in self.piano:
            # Mostra percorsi relativi alla cartella musicale per leggibilità, se possibile
            try:
                sorgente_rel = azione.sorgente.relative_to(self.parent.cartella_musicale_var.get())
                dest_rel = azione.destinazione.relative_to(self.parent.cartella_musicale_var.get())
            except ValueError:
                sorgente_rel = azione.sorgente
                dest_rel = azione.destinazione

            self.tree.insert("", tk.END, values=(str(sorgente_rel), str(dest_rel), azione.motivazione))

    def execute(self):
        self.execute_callback(self.piano)
        self.destroy()

    def cancel(self):
        self.destroy()


class AppGestoreMusicaleV0_1:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Gestore Duplicati Musicali v0.1 Alpha")
        self.root.geometry("800x600")

        # Variabili per i percorsi delle cartelle
        self.cartella_musicale_var = tk.StringVar()
        self.cartella_duplicati_var = tk.StringVar()
        self.cartella_non_conformi_var = tk.StringVar()
        self.cartella_da_verificare_var = tk.StringVar() # Variabile per il percorso DA VERIFICARE

        # Frame principale
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # ---- Sezione Selezione Cartelle ----
        cartelle_frame = ttk.LabelFrame(main_frame, text="Percorsi Cartelle", padding="10")
        cartelle_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        cartelle_frame.columnconfigure(1, weight=1)

        ttk.Label(cartelle_frame, text="Cartella Musicale:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(cartelle_frame, textvariable=self.cartella_musicale_var, width=70).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Button(cartelle_frame, text="Sfoglia...", command=lambda: self.seleziona_cartella(self.cartella_musicale_var, "Seleziona Cartella Musicale")).grid(row=0, column=2, sticky=tk.E, padx=5, pady=2)

        ttk.Label(cartelle_frame, text="Cartella Duplicati:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(cartelle_frame, textvariable=self.cartella_duplicati_var, width=70).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Button(cartelle_frame, text="Sfoglia...", command=lambda: self.seleziona_cartella(self.cartella_duplicati_var, "Seleziona Cartella per i Duplicati", True)).grid(row=1, column=2, sticky=tk.E, padx=5, pady=2)

        ttk.Label(cartelle_frame, text="Cartella Non Conformi:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(cartelle_frame, textvariable=self.cartella_non_conformi_var, width=70).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        ttk.Button(cartelle_frame, text="Sfoglia...", command=lambda: self.seleziona_cartella(self.cartella_non_conformi_var, "Seleziona Cartella per i Non Conformi", True)).grid(row=2, column=2, sticky=tk.E, padx=5, pady=2)

        # Aggiungiamo un campo (disabilitato) per mostrare il percorso "DA VERIFICARE"
        ttk.Label(cartelle_frame, text="Cartella 'Da Verificare':").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.entry_da_verificare = ttk.Entry(cartelle_frame, textvariable=self.cartella_da_verificare_var, width=70, state='readonly')
        self.entry_da_verificare.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        # Non mettiamo un bottone Sfoglia, dato che è derivato

        # ---- Area di Log ----
        log_frame = ttk.LabelFrame(main_frame, text="Log Operazioni", padding="10")
        log_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(1, weight=1) # Permette al log frame di espandersi
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
        self.log_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # ---- Pulsanti Azione ----
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        action_frame.columnconfigure(0, weight=1) # Fa sì che il pulsante di avvio sia a sinistra
        action_frame.columnconfigure(1, weight=0)
        action_frame.columnconfigure(2, weight=0)


        self.avvia_button = ttk.Button(action_frame, text="Avvia Analisi", command=self.avvia_analisi_thread)
        self.avvia_button.grid(row=0, column=0, sticky=tk.W, padx=5)

        self.pulisci_log_button = ttk.Button(action_frame, text="Pulisci Log", command=self.pulisci_log)
        self.pulisci_log_button.grid(row=0, column=1, sticky=tk.E, padx=5)

        self.stop_button = ttk.Button(action_frame, text="Interrompi (Non Impl.)", state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, sticky=tk.E, padx=5)
        
        # ---- Barra di Progresso ----
        self.progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10, padx=5)

    def seleziona_cartella(self, var_percorso, titolo_dialog, ask_save_dir=False):
        """ Apre una finestra di dialogo per selezionare una cartella. """
        percorso_selezionato = filedialog.askdirectory(title=titolo_dialog)
        if percorso_selezionato:
            var_percorso.set(percorso_selezionato)
            # Imposta default per duplicati/non conformi se non ancora specificati e se stiamo selezionando la cartella musicale
            if var_percorso == self.cartella_musicale_var: 
                path_musicale_sel = Path(percorso_selezionato)
                if not self.cartella_duplicati_var.get():
                    path_duplicati_default = path_musicale_sel / "DOPPIONI"
                    self.cartella_duplicati_var.set(str(path_duplicati_default))
                    # Imposta anche il default per DA_VERIFICARE basato sui duplicati
                    self.cartella_da_verificare_var.set(str(path_duplicati_default / "DA_VERIFICARE")) 
                if not self.cartella_non_conformi_var.get():
                    self.cartella_non_conformi_var.set(str(path_musicale_sel / "NON CONFORMI"))
            
            # Se l'utente cambia la cartella duplicati, aggiorna quella DA VERIFICARE
            elif var_percorso == self.cartella_duplicati_var:
                if self.cartella_duplicati_var.get():
                    self.cartella_da_verificare_var.set(str(Path(self.cartella_duplicati_var.get()) / "DA_VERIFICARE"))
                else: # Se cancella il percorso duplicati, cancella anche da verificare
                    self.cartella_da_verificare_var.set("")
        
    def _log_message(self, message, flush=True): # flush è per compatibilità con _default_logger
        """ Aggiunge un messaggio all'area di log della GUI. """
        if self.log_area:
            self.log_area.config(state=tk.NORMAL)
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END) # Scroll automatico all'ultimo messaggio
            self.log_area.config(state=tk.DISABLED)
            self.root.update_idletasks() # Aggiorna la GUI

    def pulisci_log(self):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state=tk.DISABLED)
        self._log_message("Log pulito.")

    def _update_progress_bar(self, corrente, totale):
        """ Aggiorna la barra di progresso della GUI. """
        if self.progress_bar:
            if totale > 0:
                percentuale = int((corrente / totale) * 100)
                self.progress_bar['value'] = percentuale
            else: # Se totale è 0, resetta la barra
                self.progress_bar['value'] = 0
            self.root.update_idletasks() # Necessario per aggiornare la GUI da un thread

    def abilita_controlli(self, abilita=True):
        stato = tk.NORMAL if abilita else tk.DISABLED
        # Abilita/Disabilita i campi di input e i bottoni sfoglia
        for child in self.root.winfo_children(): # Cerca in tutti i frame
            if isinstance(child, ttk.LabelFrame) and child.cget('text') == "Percorsi Cartelle":
                for widget in child.winfo_children():
                    if isinstance(widget, (ttk.Entry, ttk.Button)):
                         try: widget.config(state=stato) # Alcuni widget potrebbero non avere 'state'
                         except tk.TclError: pass 
            elif isinstance(child, ttk.Frame):
                 for sub_child in child.winfo_children(): # Cerca anche nei sotto-frame (es. action_frame)
                    if isinstance(sub_child, ttk.LabelFrame) and sub_child.cget('text') == "Percorsi Cartelle":
                        for widget in sub_child.winfo_children():
                            if isinstance(widget, (ttk.Entry, ttk.Button)):
                                try: widget.config(state=stato)
                                except tk.TclError: pass
                    elif isinstance(sub_child, ttk.Frame): # action_frame
                        for widget in sub_child.winfo_children():
                            if isinstance(widget, ttk.Button) and widget.cget('text') == "Avvia Analisi":
                                try: widget.config(state=stato)
                                except tk.TclError: pass
        if self.avvia_button:
            self.avvia_button.config(state=stato)
        # self.stop_button.config(state=tk.NORMAL if not abilita else tk.DISABLED) # Logica per il bottone stop


    def _esegui_spostamenti(self, piano: List[SpostaFileAzione]):
        """Esegue il piano di spostamento e logga il risultato."""
        self._log_message("\n--- Esecuzione Spostamenti Approvata dall'Utente ---")
        try:
            esegui_piano_azioni(piano, logger=self._log_message)
            self._log_message("--- Spostamenti Completati ---")
            messagebox.showinfo("Successo", f"Operazione completata. Controlla il log per i dettagli.")
        except Exception as e:
            self._log_message(f"ERRORE CRITICO DURANTE L'ESECUZIONE: {e}")
            import traceback
            self._log_message(traceback.format_exc())
            messagebox.showerror("Errore Critico", f"Si è verificato un errore irreversibile durante lo spostamento dei file:\n\n{e}")

    def _esegui_analisi(self):
        """Contiene la logica di pianificazione, da eseguire in un thread."""
        self.abilita_controlli(False)
        self.progress_bar['value'] = 0
        self._log_message("--- Avvio Analisi e Pianificazione ---")

        try:
            cartella_musicale = self.cartella_musicale_var.get()
            path_musicale = Path(cartella_musicale).resolve()
            path_duplicati = Path(self.cartella_duplicati_var.get()).resolve()
            path_non_conformi = Path(self.cartella_non_conformi_var.get()).resolve()
            path_da_verificare = Path(self.cartella_da_verificare_var.get()).resolve()

            piano = pianifica_gestione_completa(
                path_musicale,
                path_duplicati,
                path_non_conformi,
                path_da_verificare,
                logger=self._log_message,
                progress_callback=self._update_progress_bar
            )

            self.progress_bar['value'] = 100
            self._log_message("\n--- Pianificazione Completata ---")

            if not piano:
                self._log_message("Nessuna azione di spostamento necessaria.")
                messagebox.showinfo("Analisi Completata", "Nessun file duplicato o da verificare è stato trovato.")
            else:
                self._log_message(f"Trovate {len(piano)} azioni da eseguire. In attesa di conferma dall'utente...")
                # Apri la finestra di anteprima
                # Siccome stiamo aggiornando la GUI da un thread, dobbiamo usare `schedule`
                self.root.after(0, self.mostra_finestra_anteprima, piano)

        except Exception as e:
            self._log_message(f"ERRORE CRITICO DURANTE LA PIANIFICAZIONE: {e}")
            import traceback
            self.root.after(0, messagebox.showerror, "Errore Critico", f"Si è verificato un errore irreversibile durante l'analisi:\n\n{e}")
            self._log_message(traceback.format_exc())
        finally:
            # Riabilita i controlli solo se non c'è una finestra di anteprima aperta
            # La finestra di anteprima gestirà da sola la riabilitazione
            if not any(isinstance(win, PreviewWindow) for win in self.root.winfo_children()):
                 self.root.after(0, self.abilita_controlli, True)

    def mostra_finestra_anteprima(self, piano):
        PreviewWindow(self.root, piano, self._esegui_spostamenti)
        # Dopo che la finestra di anteprima è chiusa (sia per esecuzione che per annullamento),
        # riabilitiamo i controlli.
        self.abilita_controlli(True)

    def avvia_analisi_thread(self):
        """ Avvia l'analisi in un thread separato per non bloccare la GUI. """
        # Verifica preliminare che la cartella musicale sia selezionata
        if not self.cartella_musicale_var.get():
            self._log_message("ERRORE: La cartella musicale deve essere specificata.")
            tk.messagebox.showerror("Errore", "Specificare la cartella musicale prima di avviare l'analisi.")
            return
        
        # Crea e avvia il thread
        analysis_thread = threading.Thread(target=self._esegui_analisi, daemon=True)
        analysis_thread.start()

if __name__ == '__main__':
    root = tk.Tk()
    app = AppGestoreMusicaleV0_1(root)
    root.mainloop() 