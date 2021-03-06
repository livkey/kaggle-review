from utils.pd_utils.pd_db import pd_DB
from collections import namedtuple,Counter
import os
import pandas as pd
import numpy as np
from utils.utils import print_mem_time
import pickle
from utils.nlp_utils.utils import rm_stop_words,df_global_word_container,stem,\
    df_per_sample_word_lists,tf,idf,tf_idf,rm_punctuation
from utils.pypy_utils.utils import load_pickle,save_pickle,sort_value


class nlpDB(pd_DB):

    def __init__(self):   
        self.stem_dic = None
        self.sample_tfidf = None
        self.sample_words_count = None
        self.words_count = None
        self.global_idf_dic = None
        self.clean_doc = None

    def get_list(self,name,rows,text,field):
        if name == "count" or name=="tf":
            self.get_per_sample_words_count([text],field,1)
            word_list = self.sample_words_count[text] 
            if name == "tf":
                word_list = tf(word_list)
        elif name == "tfidf":
            self.get_per_sample_tfidf([text],field,1)
            word_list = self.sample_tfidf[text]
        if rows is None:
            rows = list(range(len(word_list)))
        X = []
        num_words = len(self.w2id)
        for c in rows:
            count = word_list[c]
            X.append([count.get(self.id2w[i],0) for i in range(num_words)])
        return X

    def get_clean_doc(self, texts, field, selected_words):
        if self.clean_doc is not None:
            return

        self.clean_doc = {}
        for text in texts:
            name = "{}/clean_doc_{}.p".format(self.flags.data_path,text)
            if os.path.exists(name):
                self.clean_doc[text] = pickle.load(open(name,'rb'))
            else:
                word_lists = [] # list of lists, each item is a list of words for each sample
                df_per_sample_word_lists(self.data[text],field,word_lists) 
                # this function is in place.
                clean_lists = []
                for c,word_list in enumerate(word_lists):
                    word_list = rm_stop_words(word_list)
                    word_list = rm_punctuation(word_list)
                    word_list = stem(word_list,self.stem_dic)
                    word_list = [word for word in word_list if word in selected_words]
                    clean_lists.append(word_list)
                    if c%1000 == 0:
                        print("{} docs cleaned {}".format(c,word_list[:10]))
                pickle.dump(clean_lists,open(name,'wb'))
                self.clean_doc[text] = clean_lists
        #print(self.clean_doc[text][0])

    def get_per_sample_tfidf(self, texts, field, silent=0):
        """
        Each sample is a document.
        Input:
            texts: ["train","text"]
        """
        if self.sample_tfidf is not None:
            return

        self.sample_tfidf = {}
        self.get_per_sample_words_count(texts, field, 1)

        name = "{}/global_idf_dic.p".format(self.flags.data_path)
        self.global_idf_dic = load_pickle(self.global_idf_dic,name,{})

        for text in texts:
            name = "{}/sample_tfidf_{}.p".format(self.flags.data_path,text)
            if text not in self.global_idf_dic:
                self.global_idf_dic[text] = {}
            if os.path.exists(name):
                self.sample_tfidf[text] = pickle.load(open(name,'rb'))
            else:
                tf_list = tf(self.sample_words_count[text],0)
                idf_list = idf(tf_list,self.global_idf_dic[text],0)
                tfidf_list = tf_idf(tf_list, idf_list,0)
                pickle.dump(tfidf_list,open(name,'wb'))
                self.sample_tfidf[text] = tfidf_list
            if silent==0:
                print("\n{} sample tfidf done".format(text))

        name = "{}/global_idf_dic.p".format(self.flags.data_path)
        save_pickle(self.global_idf_dic,name)



    def get_per_sample_words_count(self, texts, field, silent=0):
        """
        Each sample is a document.
        Input:
            texts: ["train","text"]
        """
        if self.sample_words_count is not None:
            return

        self.sample_words_count = {}
        self.get_global_words_count(texts,[field],1)

        for text in texts:
            name = "{}/sample_words_{}.p".format(self.flags.data_path,text)
            if os.path.exists(name):
                self.sample_words_count[text] = pickle.load(open(name,'rb'))
            else:
                word_lists = [] # list of lists, each item is a list of words for each sample
                df_per_sample_word_lists(self.data[text],field,word_lists) 
                # this function is in place.
                word_counts = []
                for word_list in word_lists:
                    word_list = rm_stop_words(word_list)
                    word_list = rm_punctuation(word_list)
                    word_list = stem(word_list,self.stem_dic)
                    word_counts.append(Counter(word_list))
                
                pickle.dump(word_counts,open(name,'wb'))
                self.sample_words_count[text] = word_counts
            if silent == 0:
                print("\n{} sample words count done".format(text))


    def get_global_words_count(self,texts,fields=["Text"],silent=0):
        """
        build self.words_count: {"train":Counter, "test":Counter}
        Input:
            texts: ["train","text"]
        """
        if self.words_count is not None:
            return

        self.words_count = {}
        name = "{}/stem_dic.p".format(self.flags.data_path)
        self.stem_dic = load_pickle(self.stem_dic,name,{})

        for text in texts:
            name = "{}/words_in_{}.p".format(self.flags.data_path,text)
            if os.path.exists(name):
            	self.words_count[text] = pickle.load(open(name,'rb'))
            else:
                word_list = []
                df_global_word_container(self.data[text],fields,word_list) 
                # global word container means this is for the entire dataset, not per sample
                # this function is in place.

                word_list = rm_stop_words(word_list)
                word_list = rm_punctuation(word_list)
                word_list = stem(word_list,self.stem_dic)
                word_count = Counter(word_list)
                pickle.dump(word_count,open(name,'wb'))
                self.words_count[text] = word_count

            if silent==0:
                print("\nnumber of different words in {}:".format(text),len(self.words_count[text]))
                k = 10
                print("Top {} most common words in {}".format(k,text), self.words_count[text].most_common(k))

        name = "{}/stem_dic.p".format(self.flags.data_path)
        save_pickle(self.stem_dic,name)

        self.global_word_count = Counter()
        for i,j in self.words_count.items():
            self.global_word_count = self.global_word_count + j

    def select_top_k_tfidf_words(self, texts, k=10, slack=8):
        name = "{}/top{}-{}_tfidf_words.p".format(self.flags.data_path,k,slack)
        selected = load_pickle(None,name,set())
        if len(selected):
            return selected
        self.get_per_sample_tfidf(['training_text','test_text'],"Text")
        for text in texts:
            data = self.sample_tfidf[text]
            for c,tfidf in enumerate(data):
                topk = sort_value(tfidf)[:k+slack]
                topk = set([i for i in topk if len(i)>2])
                selected = selected.union(topk)
                if c>0 and c%1000 == 0:
                    print("{} documents done, sample {}, num {}".format(c,topk,len(selected)))
        print(len(selected))
        name = "{}/top{}-{}_tfidf_words.p".format(self.flags.data_path,k,slack)
        save_pickle(selected,name)
        return selected

    def get_words(self,words):
        words = ["__NULL__"] + sorted(list(words))
        self.w2id = {i:c for c,i in enumerate(words)}
        self.id2w = {j:i for i,j in self.w2id.items()}


