import random
import time
from threading import Thread

import pandas as pd
from atom.api import *

FACTOR = .5


class Model(Atom):
    n = Int()
    i = Int()

    # df1 -> df2
    df_1 = Typed(pd.DataFrame)
    df_2 = Typed(pd.DataFrame)

    @observe('df_1')
    def on_df_1(self, change):
        # print(f'{self.df_1 = }')

        df_2 = self.df_1.copy()
        df_2['value x n'] = df_2['value'] * self.n

        self.df_2 = df_2

    @observe('df_2')
    def on_df_2(self, change):
        print(f'\n\nnew {self.df_2 = }\n\n')

    @observe('n')  # order book tick
    def on_n(self, change):
        # print(f'{self.i}  ->  {self.n}')
        self.i += 1

        if self.df_2 is not None:
            self.df_2['value x n'] = self.df_2['value'] * self.n



def tick(model):
    while True:
        model.n = random.randint(-100_000, 100_000)
        time.sleep(1 * FACTOR)


def update_df(model):
    """Another thread that updates less frequently the dataframe.
    """
    while True:
        fruits = ['apple', 'banana', 'cherry', 'melon', 'pear']
        df = pd.DataFrame()
        picked_fruits = random.sample(fruits, random.randint(1, 5))
        df['fruit'] = picked_fruits
        values = random.sample(range(1, 11), len(df))
        df['value'] = values
        model.df_1 = df
        time.sleep(10 * FACTOR)


def print_df_2(model):
    while True:
        # print(f'\n\n{model.df_2 = }\n{id(model.df_2) = }\n')
        time.sleep(1 * FACTOR)


def main(model=None):
    if model is None:
        model = Model()

    t = Thread(target=tick, args=(model,), daemon=True)
    t.start()

    t2 = Thread(target=update_df, args=(model,), daemon=True)
    t2.start()

    t3 = Thread(target=print_df_2, args=(model,), daemon=True)
    t3.start()

    return t, t2, t3


if __name__ == '__main__':
    t1, t2, t3 = main()
    t1.join()
    t2.join()
    t3.join()
