from matplotlib import pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

def line_plot(report, df, x, metrices, title=None):
    # Plot day average  and perform anova of k-means
    df.plot(x=x, y=metrices, kind="bar", figsize=(12, 8))
    if title is None:
        title = "plot of " + metrices[0]
    plt.title(title, fontsize=20)
    report.savefig()
    plt.close()

def box_plot(report, df, metric, title=None):
    # Plot day average  and perform anova of k-means
    ax = df.boxplot(metric, figsize=(12, 8))
    #columns_my_order = df[group]
    #ax.set_xticklabels(columns_my_order)
    if title is None:
        title = "box plot of " + metric
    plt.title(title, fontsize=20)
    report.savefig()
    plt.close()



def box_plot_by_group(report, df, metric, group, title=None,filter={}, rotation_x=0):
    # Plot day average  and perform anova of k-means

    #columns_my_order = df[group]
    #ax.set_xticklabels(columns_my_order)
    if title is None:
        title = metric + ' over ' + group

    for key, value in filter.items():
        df = df[df[key] == value]
        desc = value if isinstance(value, str) else str(value)
        title = title + " for " + desc + " "

    ax = df.boxplot(metric, by=group, figsize=(12, 8))
    plt.title(title, fontsize=20)
    plt.xticks(rotation=rotation_x)
    report.savefig()
    plt.close()



def plot_histogram(report, df_input, metric, filter={}, bins=10, title=None):
    if title is None:
        title = 'Histogram of ' + metric

    df = df_input
    for key, value in filter.items():
        df = df[df[key] == value]
        desc = value if isinstance(value, str) else str(value)
        title = 'Histogram of ' + metric + " for " + desc + " "
    df[metric].hist(weights=np.ones_like(df[df.columns[0]]) * 100. / len(df), bins=bins, grid=False,figsize=(12,8))
    plt.title(title, fontsize=20)
    report.savefig()
    plt.close()


def plot_scatter(report, df_input, x, y, s, filter={}, title=None):
    if title is None:
        title = 'Scatter plot of ' + x + " vs " + y
    df = df_input
    for key, value in filter.items():
        df = df[df[key] == value]
        desc = value if isinstance(value, str) else str(value)
        title = 'Scatter plot of ' + x + " vs " + y + " for " + desc
    df.plot.scatter(x=x, y=y, s=s)
    plt.title(title, fontsize=10)
    report.savefig()
    plt.close()


def Plot3D_O(report, df, x,y,z):
    threedee = plt.figure().gca(projection='3d')
    threedee.scatter(df[x], df[y], df[z])
    threedee.set_xlabel(x)
    threedee.set_ylabel(y)
    threedee.set_zlabel(z)
    report.savefig()
    plt.close()

def Plot3D(report, df, x,y,z):
    threedee = plt.figure()
    X, Y = np.meshgrid(df[x], df[y])
    ax = plt.axes(projection='3d')
    #ax.contour3D(X,Y, df[z], cmap='binary')
    #ax.plot_surface(X, Y, df[z], rstride=1, cstride=1, cmap='viridis', edgecolor='none')
    #ax.plot_trisurf(df[x], df[y],  df[z], linewidth=0, antialiased=False)
    ax.scatter( df[y], df[z],df[x], c='r', marker='o')
    ax.view_init(20, 60)

    ax.set_xlabel(y)
    ax.set_ylabel(z)
    ax.set_zlabel(x)

    report.savefig()
    plt.close()

def day_open_statistics(open_candle, first_15_mins, yday_profile):
    open_low = open_candle['open']
    open_high = open_candle['open']
    type = 0
    txt = ""
    if open_low > yday_profile['high']:
        txt += "open above prev high"
        type = 1
        if first_15_mins['low'] >= yday_profile['high']:
            txt += "\ngap up sustained"
        elif first_15_mins['low'] >= yday_profile['va_h_p']:
            txt += "\nvalue area sustained"
        elif first_15_mins['low'] >= yday_profile['poc_price']:
            txt += "\nPOC  sustained"
        elif first_15_mins['low'] >= yday_profile['va_l_p']:
            txt += "\nSupport at value area "
        elif first_15_mins['low'] >= yday_profile['low']:
            txt += "\nSupport at prev low"
        else:
            txt += "\nprev low breached"

    elif open_low > yday_profile['va_h_p']:
        txt += "open above prev value area"
        type = 2
        if first_15_mins['high'] >= yday_profile['high']:
            txt += "\nprev day high breached"
        else:
            txt += "\nResistance at prev day high"
        if first_15_mins['low'] >= yday_profile['va_h_p']:
            txt += "\nvalue area sustained"
        elif first_15_mins['low'] >= yday_profile['poc_price']:
            txt += "\nPOC  sustained"
        elif first_15_mins['low'] >= yday_profile['va_l_p']:
            txt += "\nSupport in Value area "
        elif first_15_mins['low'] >= yday_profile['low']:
            txt += "\nSupport at prev low"
        else:
            txt += "\nprev low breached"

    elif open_high < yday_profile['low']:
        txt += "open below prev low"
        type = 5
        if first_15_mins['high'] <= yday_profile['low']:
            txt += "\ngap down sustained"
        elif first_15_mins['high'] <= yday_profile['va_l_p']:
            txt += "\nvalue area sustained"
        elif first_15_mins['high'] <= yday_profile['poc_price']:
            txt += "\nPOC  sustained"
        elif first_15_mins['low'] >= yday_profile['va_l_p']:
            txt += "\nSupport at prev value area "
        elif first_15_mins['high'] <= yday_profile['high']:
            txt += "\nSupport at prev high"
        else:
            txt += "\nprev high breached"

    elif open_high < yday_profile['va_l_p']:
        txt += "open below prev value area"
        type = 4
        if first_15_mins['low'] <= yday_profile['low']:
            txt += "\nprev day low breached"
        else:
            txt += "\nSupport at prev day low"
        if first_15_mins['high'] <= yday_profile['va_l_p']:
            txt += "\nvalue area sustained"
        elif first_15_mins['high'] <= yday_profile['poc_price']:
            txt += "\nPOC  sustained"
        elif first_15_mins['high'] <= yday_profile['va_h_p']:
            txt += "\nResistance at Value area "
        elif first_15_mins['high'] <= yday_profile['high']:
            txt += "\nResistance at prev high"
        else:
            txt += "\nprev high breached"

    else:
        txt += "open in prev value area range"
        type = 3
        if first_15_mins['high'] >= yday_profile['high']:
            txt += "\nprev day high breached"
        elif first_15_mins['high'] >= yday_profile['va_h_p']:
            txt += "\nValue area high breached"
        else:
            txt += "\nHigh in range"
        if first_15_mins['low'] <= yday_profile['va_l_p']:
            txt += "\nValue area low breached"
        elif first_15_mins['low'] <= yday_profile['low']:
            txt += "\nprev day low breached"
        else:
            txt += "\nLow in range"
    return txt

def plot_profile_chart(ax,df,c_date,remove_y_label=False, ini_bal=False,text=None, xlim=15):
    title = c_date + ("_ini bal" if ini_bal else "")
    if df.shape[0] > 100:
        fontsize = 3
    else:
        fontsize = 4
    fig_size = (7.33, 5) if not ini_bal else (3, 5)
    df.plot.barh(ax=ax, legend=False, stacked=True, figsize=fig_size, fontsize=fontsize, title=title,width=0.5,color='w')
    ax.bar_height = 0.1  # probable doesn't work
    ax.title.set_size(8)
    plt.tight_layout()
    # ax.legend(bbox_to_anchor=(1, 1.01), loc='upper left')
    for spine in plt.gca().spines.values():
        spine.set_visible(False)
    if ini_bal:
        ax.set_xlim(0, 10)
    else:
        ax.set_xlim(0, xlim)

    ax.xaxis.set_tick_params(length=0, labelbottom=False)
    ax.yaxis.set_tick_params(length=0)  # removes dash
    if remove_y_label:
        ax.yaxis.set_tick_params(labelbottom=False)  # removes label
    #ax.vlines(x=2, linewidth=2, ymin=0, ymax=20000, color='r')
    #ax.hlines(y=10840, linewidth=2, xmin=0, xmax=100, color='r')
    #plt.axhline(int(processed_data['value_area_price'][1]))
    #plt.axvline(2)
    #plt.axhline(10)

    # ax.set_yticklabels([])
    # hide boarder
    # ax.set_color('r')
    if text is not None:
        ax.text(3, 10, text, fontsize=6, style='italic', bbox={'facecolor': 'white', 'alpha': 0.5, 'pad': 5})
    cols = df.columns
    for c, col in zip(ax.containers, cols):
        # create a custom label for bar_label
        vals = df[col]
        labels = [col if (w := v.get_width()) > 0 else '' for v, val in zip(c, vals)]
        # annotate each section with the custom labels
        ax.bar_label(c, labels=labels, label_type='center', fontsize=fontsize)


