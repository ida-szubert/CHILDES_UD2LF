from preprocess import *
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# eng_tokens = 107895
# heb_tokens = 64478

# get English UD stats
eng_parse_dict = read_conll_file("../conll/full_adam/adam.all.conll.txt", english=True)
eng_dep_freq = get_dep_stats(eng_parse_dict, write_out=False)
eng_dep_freq_norm = {}
eng_tokens = sum(eng_dep_freq.values())
for dep,f in eng_dep_freq.items():
    eng_dep_freq_norm[dep] = float(f)/eng_tokens


# get Hebrew UD stats
heb_parse_dict = read_conll_file("../conll/full_sivan/sivan.all.conll.txt", english=False)
heb_dep_freq = get_dep_stats(heb_parse_dict, write_out=False)
heb_dep_freq_norm = {}
heb_tokens = sum(heb_dep_freq.values())
for dep,f in heb_dep_freq.items():
    heb_dep_freq_norm[dep] = float(f)/heb_tokens


data = []
for dep in eng_dep_freq_norm.keys():
    if dep in heb_dep_freq_norm.keys():
        data.append([dep, eng_dep_freq_norm[dep], heb_dep_freq_norm[dep]])
df = pd.DataFrame(data, columns=['dependency','Adam','Hagar'])

df_eng_more = pd.melt(df[df['Adam'] > df['Hagar']+0.005], id_vars=['dependency'], var_name='corpus', value_name='count per token')
df_heb_more = pd.melt(df[df['Adam']+0.005 < df['Hagar']], id_vars=['dependency'], var_name='corpus', value_name='count per token')

sns.set()
g = sns.lmplot(x="dependency", y="count per token", data=df_eng_more, fit_reg=False, hue='corpus', legend=False)
g.set(ylim=(None, 0.22))
g.set_xticklabels(rotation=90)
plt.legend(loc='upper right')
g.savefig('eng_more.png')
# plt.show()

g = sns.lmplot(x="dependency", y="count per token", data=df_heb_more, fit_reg=False, hue='corpus', legend=False)
g.set(ylim=(None, 0.22))
g.set_xticklabels(rotation=90)
plt.legend(loc='upper right')
g.savefig('heb_more.png')
# plt.show()

#################################


