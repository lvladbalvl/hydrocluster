#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  5 13:19:39 2018

@author: lashkov
"""

import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from tkinter.messagebox import askyesno
from tkinter.messagebox import showerror
from tkinter.messagebox import showinfo

try:
    from sklearn.cluster import DBSCAN
    from sklearn.metrics import silhouette_score
    from sklearn.metrics import calinski_harabaz_score
except ImportError:
    showerror('Ошибка!', 'Библиотека scikit-learn не установлена!')
    sys.exit()

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title('HydroCluster')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', self.close_win)
        self.menu()
        fra1 = tk.Frame(self)
        fra1.grid(row=0, column=0)
        lab1 = tk.LabelFrame(fra1, text='EPS (\u212B)', labelanchor='n', borderwidth=5)
        lab1.grid(row=0, column=0, pady=5, padx=5)
        self.sca1 = tk.Scale(lab1, length=300, from_=1.0, to=10.0, showvalue=1, orient=tk.HORIZONTAL, resolution=0.1)
        self.sca1.pack()
        lab2 = tk.LabelFrame(fra1, text='MIN_SAMPLES', labelanchor='n', borderwidth=5)
        lab2.grid(row=0, column=1, pady=5, padx=5)
        self.sca2 = tk.Scale(lab2, length=300, from_=1, to=10, showvalue=1, orient=tk.HORIZONTAL)
        self.sca2.pack()
        but1 = tk.Button(fra1, text='Старт!', command=lambda: self.run(auto=False))
        but1.grid(row=0, column=2, padx=10)
        but2 = tk.Button(fra1, text='Авто', command=lambda: self.run(auto=True))
        but2.grid(row=0, column=3, padx=10)
        lab3 = tk.LabelFrame(fra1, text='Метрика автоподбора', labelanchor='n', borderwidth=5)
        lab3.grid(row=0, column=4, pady=5, padx=5)
        listbox_items = ['si_score', 'calinski']
        self.combox = ttk.Combobox(lab3, height=5, width=15, values=listbox_items)
        self.combox.pack()
        self.combox.set('si_score')
        self.fra2 = tk.Frame(self, width=1024, height=650)
        self.fra2.grid(row=1, column=0)
        self.fra2.grid_propagate(False)
        fra3 = tk.Frame(self)
        fra3.grid(row=2, column=0, pady=10)
        self.tx = tk.Text(fra3, width=120, height=10)
        scr = tk.Scrollbar(fra3, command=self.tx.yview)
        self.tx.configure(yscrollcommand=scr.set, state='disabled')
        self.tx.pack(side=tk.LEFT)
        scr.pack(side=tk.RIGHT, fill=tk.Y)
        self.tx.bind('<Enter>', lambda e: self._bound_to_mousewheel(e, self.tx))
        self.tx.bind('<Leave>', self._unbound_to_mousewheel)
        self.run_flag = False
        self.s_array = None
        self.run_flag = False
        self.fig = None
        self.canvas = None
        self.toolbar = None
        self.grid = False
        self.legend = False
        self.cls = ClusterPdb()

    def _bound_to_mousewheel(self, event, tx):
        self.bind_all("<MouseWheel>", lambda e: self._on_mousewheel(e, tx))
        self.bind_all('<Button-4>', lambda e: self._on_mousewheel(e, tx))
        self.bind_all('<Button-5>', lambda e: self._on_mousewheel(e, tx))
        self.bind_all('<Up>', lambda e: self._on_mousewheel(e, tx))
        self.bind_all('<Down>', lambda e: self._on_mousewheel(e, tx))

    def _unbound_to_mousewheel(self, event):
        self.unbind_all("<MouseWheel>")
        self.unbind_all('<Button-4>')
        self.unbind_all('<Button-5>')
        self.unbind_all('<Up>')
        self.unbind_all('<Down>')

    @staticmethod
    def _on_mousewheel(event, tx):
        if event.num == 4 or event.keysym == 'Up':
            tx.yview_scroll(-1, "units")
        elif event.num == 5 or event.keysym == 'Down':
            tx.yview_scroll(1, "units")
        else:
            tx.yview_scroll(int(-1 * (event.delta / 120)), "units")

    @staticmethod
    def about():
        showinfo('Информация', 'Построение зависимости расстояния\nмежду центрами масс доменов белка от времени МД')

    def menu(self):
        """Метод инициалиции меню"""
        m = tk.Menu(self)  # создается объект Меню на главном окне
        self.config(menu=m)  # окно конфигурируется с указанием меню для него
        fm = tk.Menu(m)  # создается пункт меню с размещением на основном меню (m)
        # пункту располагается на основном меню (m)
        m.add_cascade(label='Файл', menu=fm)
        # формируется список команд пункта меню
        fm.add_command(label='Открыть PDB', command=self.open_pdb)
        fm.add_command(label='Сохранить рисунок', command=self.save_graph)
        fm.add_command(label='Сохранить LOG', command=self.save_log)
        fm.add_command(label='Выход', command=self.close_win)
        om = tk.Menu(m)  # создается пункт меню с размещением на основном меню (m)
        # пункту располагается на основном меню (m)
        m.add_cascade(label='Опции', menu=om)
        om.add_command(label='Сетка графика', command=self.grid_set)
        om.add_command(label='Легенда', command=self.legend_set)
        om.add_command(label='Статистика', command=self.resi)
        m.add_command(label='Справка', command=self.about)

    def close_win(self):
        """Самоуничтожение с вопросом"""
        if askyesno('Выход', 'Вы точно хотите выйти?'):
            self.destroy()

    def run(self, auto=False):
        """Основной алгоритм программы"""
        if self.run_flag:
            showerror('Ошибка!', 'Расчет уже идёт!')
            return
        self.run_flag = True
        if auto:
            metric = self.combox.get()
            try:
                eps, min_samples = self.cls.auto(metric=metric)
            except ValueError:
                showerror('Ошибка!', 'Не загружен файл\nили ошибка кластерного анализа!')
                self.run_flag = False
                return
            self.sca1.set(eps)
            self.sca2.set(min_samples)
        else:
            eps = self.sca1.get()
            min_samples = self.sca2.get()
            try:
                self.cls.cluster(eps, min_samples)
            except ValueError:
                showerror('Ошибка!', 'Не загружен файл\nили ошибка кластерного анализа!')
                self.run_flag = False
                return
        self.tx.configure(state='normal')
        self.tx.insert(tk.END,
                       "Estimated number of clusters: {0:d}\nSilhouette Coefficient: {1:.3f}\nCalinski and Harabaz score: {4:.3f}\nEPS: {2:.1f} \u212B\nMIN_SAMPLES: {3:d}\n".format(
                           self.cls.n_clusters, self.cls.si_score, eps, min_samples, self.cls.calinski))
        self.tx.configure(state='disabled')
        self.graph()
        self.run_flag = False

    def graph(self):
        try:
            self.canvas.get_tk_widget().destroy()
            self.toolbar.destroy()
        except AttributeError:
            pass
        self.fig = Figure(figsize=(8, 6))
        try:
            unique_labels = set(self.cls.labels)
        except AttributeError:
            return
        ax = axes3d.Axes3D(self.fig)
        colors = [plt.cm.Spectral(each) for each in np.linspace(0, 1, len(unique_labels))]
        for k, col in zip(unique_labels, colors):
            class_member_mask = (self.cls.labels == k)
            if k == -1:
                # Black used for noise.
                xyz = self.cls.X[class_member_mask & ~self.cls.core_samples_mask]
                ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], c='k', s=12, label="Noise")
            else:
                xyz = self.cls.X[class_member_mask & self.cls.core_samples_mask]
                ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], c=tuple(col), s=32, label="Core Cluster No {:d}".format(k))
                xyz = self.cls.X[class_member_mask & ~self.cls.core_samples_mask]
                ax.scatter(xyz[:, 0], xyz[:, 1], xyz[:, 2], c=tuple(col), s=12, label="Added Cluster No {:d}".format(k))
        self.fig.suptitle("Cluster analysis\n")
        ax.set_ylabel(r'$y\ \AA$')
        ax.set_xlabel(r'$x\ \AA$')
        ax.set_zlabel(r'$z\ \AA$')
        ax.grid(self.grid)
        if self.legend:
            ax.legend(loc='best', frameon=False)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.fra2)
        ax.mouse_init()
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self.fra2)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(fill=tk.BOTH, side=tk.TOP, expand=1)

    def open_pdb(self):
        if self.run_flag:
            showerror('Ошибка!', 'Расчет уже идёт!')
            return
        opt = {'filetypes': [('Файлы PDB', ('.pdb', '.PDB', '.ent')), ('Все файлы', '.*')]}
        pdb = askopenfilename(**opt)
        if pdb:
            try:
                with open(pdb) as f:
                    s_array = f.readlines()
            except FileNotFoundError:
                return
            else:
                showinfo('Информация', 'Файл прочитан!')
                self.cls.clean()
            try:
                self.cls.parser(s_array)
            except ValueError:
                showerror('Ошибка', 'Неверный формат\nлибо файл не содержит гидрофоьных остатков!')
                return
        else:
            return
        try:
            self.canvas.get_tk_widget().destroy()
            self.toolbar.destroy()
        except AttributeError:
            pass
        self.fig = None
        self.tx.configure(state='normal')
        self.tx.delete('1.0', tk.END)
        self.tx.configure(state='disabled')

    def save_log(self):
        opt = {'parent': self, 'filetypes': [('LOG', '.log'), ], 'initialfile': 'myfile.log', 'title': 'Сохранить LOG'}
        sa = asksaveasfilename(**opt)
        if sa:
            letter = self.tx.get(1.0, tk.END)
            try:
                with open(sa, 'w') as f:
                    f.write(letter)
            except FileNotFoundError:
                pass

    def save_graph(self):
        if self.run_flag:
            showerror('Ошибка!', 'Расчет не закончен!')
            return
        if self.fig is None:
            showerror('Ошибка!', 'График недоступен!')
            return
        opt = {'parent': self, 'filetypes': [('Все поддерживаесые форматы', (
            '.eps', '.jpeg', '.jpg', '.pdf', '.pgf', '.png', '.ps', '.raw', '.rgba', '.svg', '.svgz', '.tif',
            '.tiff')), ],
               'initialfile': 'myfile.png', 'title': 'Сохранить график'}
        sa = asksaveasfilename(**opt)
        if sa:
            try:
                self.fig.savefig(sa, dpi=600)
            except FileNotFoundError:
                return
            except AttributeError:
                showerror('Ошибка!', 'График недоступен!')
            except ValueError:
                showerror('Неподдерживаемый формат файла рисунка!',
                          'Поддреживаемые форматы: eps, jpeg, jpg, pdf, pgf, png, ps, raw, rgba, svg, svgz, tif, tiff.')

    def grid_set(self):
        self.grid = bool(askyesno('Cетка', 'Отобразить?'))
        if self.run_flag:
            return
        try:
            self.canvas.get_tk_widget().destroy()
            self.toolbar.destroy()
        except AttributeError:
            pass
        self.graph()

    def legend_set(self):
        self.legend = bool(askyesno('Легенда', 'Отобразить?'))
        if self.run_flag:
            return
        try:
            self.canvas.get_tk_widget().destroy()
            self.toolbar.destroy()
        except AttributeError:
            pass
        self.graph()

    def resi(self):
        if self.run_flag:
            showerror('Ошибка!', 'Расчет уже идёт!')
            return
        aa_list = self.cls.aa_list
        if (not aa_list) or self.cls.labels is None:
            return
        aa_list = list(zip(aa_list, self.cls.labels, self.cls.core_samples_mask))
        for k in sorted(set(self.cls.labels)):
            if k != -1:
                self.tx.configure(state='normal')
                self.tx.insert(tk.END, "\nIn core cluster No {:d} included: ".format(k))
                self.tx.configure(state='disabled')
                for aa in aa_list:
                    if aa[1] == k and aa[2]:
                        self.tx.configure(state='normal')
                        self.tx.insert(tk.END, "{2:s}:{1:s}{0:d} ".format(*aa[0]))
                        self.tx.configure(state='disabled')
        self.tx.configure(state='normal')
        self.tx.insert(tk.END, "\n\n")
        self.tx.configure(state='disabled')


class ClusterPdb:
    def __init__(self):
        self.X = None
        self.labels = None
        self.core_samples_mask = []
        self.n_clusters = 0
        self.si_score = -1
        self.calinski = 0
        self.weight_array = []
        self.aa_list = []

    def clean(self):
        self.X = None
        self.labels = None
        self.core_samples_mask = []
        self.n_clusters = 0
        self.si_score = -1
        self.calinski = 0
        self.weight_array = []
        self.aa_list = []

    def cluster(self, eps, min_samples):
        if self.X is None:
            raise ValueError
        db = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=-1).fit(self.X, sample_weight=self.weight_array)
        # The DBSCAN algorithm views clusters as areas of high density separated by areas of low density.
        # Due to this rather generic view, clusters found by DBSCAN can be any shape,
        # as opposed to k-means which assumes that clusters are convex shaped.
        # The central component to the DBSCAN is the concept of core samples, which are samples that are in areas
        # of high density. A cluster is therefore a set of core samples,
        # each close to each other (measured by some distance measure) and a set of non-core samples that are close
        # to a core sample (but are not themselves core samples).
        # There are two parameters to the algorithm, min_samples and eps, which define formally what we mean when we say dense.
        # Higher min_samples or lower eps indicate higher density necessary to form a cluster.
        # Cite:
        # “A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases with Noise”
        # Ester, M., H. P. Kriegel, J. Sander, and X. Xu,
        # In Proceedings of the 2nd International Conference on Knowledge Discovery and Data Mining,
        # Portland, OR, AAAI Press, pp. 226–231. 1996
        self.core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        self.core_samples_mask[db.core_sample_indices_] = True
        self.labels = db.labels_
        self.n_clusters = len(set(self.labels)) - (1 if -1 in self.labels else 0)
        try:
            self.si_score = silhouette_score(self.X, self.labels)
        # The Silhouette Coefficient is calculated using the mean intra-cluster distance (a)
        # and the mean nearest-cluster distance (b) for each sample.
        # The Silhouette Coefficient for a sample is (b - a) / max(a, b).
        # To clarify, b is the distance between a sample and the nearest cluster that the sample is not a part of.
        # Note that Silhouette Coefficient is only defined if number of labels is 2 <= n_labels <= n_samples - 1.
        # Cite:
        # Peter J. Rousseeuw (1987). “Silhouettes: a Graphical Aid to the Interpretation and Validation of Cluster Analysis”.
        # Computational and Applied Mathematics 20: 53-65.
        except ValueError:
            self.si_score = -1
        try:
            self.calinski = calinski_harabaz_score(self.X, self.labels)
            # The score is defined as ratio between the within-cluster dispersion and the between-cluster dispersion.
            # Cite:
            # T.Calinski and J.Harabasz, 1974. “A dendrite method for cluster analysis”.Communications in Statistics
        except ValueError:
            self.calinski = 0

    def auto(self, metric='si_score'):
        states = []
        for i in range(1, 11):
            j = 1.0
            while j < 10.0:
                print(i, j)
                self.cluster(eps=j, min_samples=i)
                states.append(
                    (self.labels, self.core_samples_mask, self.n_clusters, self.si_score, self.calinski, j, i))
                j += 0.1
        if metric == 'si_score':
            states.sort(key=lambda x: x[3], reverse=True)
        elif metric == 'calinski':
            states.sort(key=lambda x: x[4], reverse=True)
        state = states[0]
        self.labels = state[0]
        self.core_samples_mask = state[1]
        self.n_clusters = state[2]
        self.si_score = state[3]
        self.calinski = state[4]
        return state[5], state[6]

    def parser(self, strarr):
        xyz_array = []
        # www.pnas.org/cgi/doi/10.1073/pnas.1616138113 # 1.0 - -7.55 kj/mol A;; residues with delta mu < 0
        hydrfob = {'ALA': 1.269, 'VAL': 1.094, 'PRO': 1.0, 'LEU': 1.147, 'ILE': 1.289, 'PHE': 1.223, 'MET': 1.013,
                   'TRP': 1.142, 'CYS': 0.746, 'GLY': 0.605, 'THR': 0.472}
        # OLD CA-BASED PARSER
        # for s in strarr:
        #     if s[0:6] == 'ATOM  ' and (s[17:20] in hydrfob) and s[12:16] == ' CA ':
        #         xyz = [float(s[30:38]), float(s[38:46]), float(s[46:54])]
        #         xyz_array = np.hstack((xyz_array, xyz))
        #         self.weight_array.append(hydrfob[s[17:20]])
        xyzm_array = []
        current_resn = None
        current_chainn = None
        current_resname = None
        mass = {
            ' H': 1.0,
            ' C': 12.0,
            ' N': 14.0,
            ' O': 16.0,
            ' P': 31.0,
            ' S': 32.0,
            ' F': 19.0}
        for s in strarr:
            if s[0:6] == 'ATOM  ' and (s[17:20] in hydrfob) and ((current_resn is None and current_chainn is None) or (
                    current_resn == int(s[22:26]) and current_chainn == s[21])):
                current_resn = int(s[22:26])
                current_chainn = s[21]
                current_resname = s[17:20]
                xyzm = [float(s[30:38]), float(s[38:46]), float(s[46:54]), mass[s[76:78]]]
                xyzm_array = np.hstack((xyzm_array, xyzm))
            elif s[0:6] == 'ATOM  ' and (s[17:20] in hydrfob) and not (
                    (current_resn is None and current_chainn is None) or (
                    current_resn == int(s[22:26]) and current_chainn == s[21])):
                self.aa_list.append((current_resn, current_chainn, current_resname))
                self.weight_array.append(hydrfob[current_resname])
                try:
                    xyzm_array.shape = (-1, 4)
                except AttributeError:
                    raise ValueError
                print(self._cmass(xyzm_array))
                xyz_array = np.hstack((xyz_array, self._cmass(xyzm_array)))
                xyzm_array = []
                current_resn = int(s[22:26])
                current_chainn = s[21]
                current_resname = s[17:20]
                xyz = [float(s[30:38]), float(s[38:46]), float(s[46:54]), mass[s[76:78]]]
                xyzm_array = np.hstack((xyzm_array, xyz))
        try:
            xyz_array.shape = (-1, 3)
        except AttributeError:
            raise ValueError
        self.X = xyz_array

    @staticmethod
    def _cmass(str_nparray: np.ndarray) -> list:
        """Вычисление положения центра массс"""
        mass_sum = float(str_nparray[:, 3].sum())
        mx = (str_nparray[:, 3]) * (str_nparray[:, 0])
        my = (str_nparray[:, 3]) * (str_nparray[:, 1])
        mz = (str_nparray[:, 3]) * (str_nparray[:, 2])
        c_mass_x = float(mx.sum()) / mass_sum
        c_mass_y = float(my.sum()) / mass_sum
        c_mass_z = float(mz.sum()) / mass_sum
        return [c_mass_x, c_mass_y, c_mass_z]


def win():
    """Главная функция окна"""
    app = App()
    app.mainloop()


if __name__ == '__main__':
    win()
