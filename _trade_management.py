import pandas as pd
import numpy as np
import time
import io
import unittest
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import (RandomForestClassifier, ExtraTreesClassifier, AdaBoostClassifier,\
                              GradientBoostingClassifier)
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn import metrics
from sklearn.linear_model import LogisticRegression
import statistics 
class Model_Selection:
    
    def __init__(self,models,model_grid_params,data_2014,latest_sec,pred_sec,day):
        
        self.models = models
        self.model_grid = model_grid_params
        self.data_2014 = data_2014
        self.latest_sec = latest_sec
        self.pred_sec = pred_sec
        self.day = day
        self.keys = models.keys()
        self.best_score = {}
        self.grid = {}
        self.predict_values = {}
        self.cv_acc = {}
        self.acc = {}
        self.fscore = {}
        self.true_values = {}
        self.predict_values_day = {}
        self.cv_acc_day = {}
        self.acc_day = {}
        self.fscore_day = {}
        self.true_values_day = {}
        self.summary_day = []
        self.cv = 2
        
    def Grid_fit(self,X_train,y_train,cv = 2,scoring = 'accuracy'):
        self.cv = cv
        # Tune parameters for each model in self.keys
        for key in self.keys:
            model = self.models[key]
            model_grid = self.model_grid[key]
            Grid = GridSearchCV(model, model_grid, cv = cv, scoring = scoring)
            Grid.fit(X_train,y_train) 
            self.grid[key] = Grid
            self.cv_acc[key].append(Grid.best_score_)  
            

    def model_fit(self,X_train, y_train, X_test, y_test):

        for key in self.keys:

            # define model/algorithm here
            # set parameter using the best_params_ obtained after calling Grid_fit (assume you have already called Grid_fit)
            # fit model with X_train and y_train
            # predict using trained model on X_test
            # Calculate accuracy and f1_score

            model = self.models[key]
            model.set_params(**self.grid[key].best_params_)
            model.fit(X_train, y_train)
            predictions = model.predict(X_test)
            #print 'Prediction latest 15 second = %s'%(predictions)
            self.predict_values[key].append(predictions.tolist())
            self.true_values[key].append(y_test.tolist())
            acc = metrics.accuracy_score(y_test,predictions)
            f_score = metrics.f1_score(y_test,predictions)
            self.acc[key].append(acc)
            self.fscore[key].append(f_score)
            
            if key == 'SVC':
                if list(self.grid[key].best_params_.values())[0] == 'linear':
                    feature_imp = dict(zip([i for i in range(0,64,1)],model.coef_[0]))
                    Top_five = sorted(feature_imp.items(),key = lambda x : x[1] , reverse=True)[0:5]
                else:
                    pass
            else: 
                feature_imp = dict(zip([i for i in range(0,64,1)],model.feature_importances_))
                Top_five = sorted(feature_imp.items(),key = lambda x : x[1] , reverse=True)[0:5]
                pass

    def pipline(self):
        # This is the main method, where you train algorithms for each set of 
        # hyperparameters on each day. And store statistics in the mean time.
        
        # looping through days (in our case, the we only have the data for one day 50 seconds)
        self.set_list_day()
        for day in range(0,self.day,1):
            # call set_list() to initialize the corresponding properties
            # call set_list_day() to initialize the corresponding properties
            self.set_list() 
            # don't print
            for i in range(0, 20, self.pred_sec):
                # only two rolling windows here
                # for data in each day for each rolling window of training and test data
                # run grid_fit to find best parameter for each algorithm
                # then run model_fit to obtain stats for algorithms
                # Remember, label is the first column of data and the remaining columns are features
                data_train = self.data_2014[day][i:i+self.latest_sec]
                X_train = data_train.drop(['0'],axis=1)#,'65','66','67'],axis=1)
                y_train = data_train['0']

                data_test = self.data_2014[day][i + self.latest_sec:i + self.latest_sec + self.pred_sec]
                X_test = data_test.drop(['0'],axis=1)#,'65','66','67'],axis=1)
                y_test = data_test['0']
                
                self.Grid_fit(X_train, y_train, cv = self.cv, scoring = 'accuracy')
                self.model_fit(X_train, y_train,X_test,y_test)

                
            for key in self.keys:
                # append values of set_list properties to set_list_day properties
                self.cv_acc_day[key].append(self.cv_acc[key])
                self.acc_day[key].append(self.acc[key])
                self.fscore_day[key].append(self.fscore[key])
                self.true_values_day[key].append(self.true_values[key])
                self.predict_values_day[key].append(self.predict_values[key])

            # append score_summary(sort_by = 'Accuracy_mean')) to summary_day
            self.summary_day.append(self.score_summary(sort_by = 'Accuracy_mean'))
    
    def set_list(self):
        # Initialize predict_values, cv_acc, acc, fscore, true_values properties (these are stats for a specific day)
        # for each method in self.keys, the corresponding value of the above dictionaries are empty list
        for key in self.keys:
            self.predict_values[key] = []
            self.cv_acc[key] = []
            self.acc[key] = []
            self.fscore[key] = []
            self.true_values[key] = []
            
    def set_list_day(self):
        # Initialize predict_values_day, cv_acc_day, acc_day, fscore_day, true_values_day properties (these are stats for all days)
        # for each method in self.keys, the corresponding value of the above dictionaries are empty list
        for key in self.keys:
            self.predict_values_day[key] = []
            self.cv_acc_day[key] = []
            self.acc_day[key] = []
            self.fscore_day[key] = []
            self.true_values_day[key] = []
            

      
    def score_summary(self,sort_by):
        #
        # summary looks like 
        #
        #                                 Estimator  Accuracy_mean  Accuracy_std  \
        # Ranking                                                            
        # 0            RandomForestClassifier           0.65          0.35   
        # 1              ExtraTreesClassifier           0.65          0.35   
        # 3        GradientBoostingClassifier           0.65          0.35   
        # 4                               SVC           0.65          0.35   
        # 2                AdaBoostClassifier           0.40          0.10   

        #         Accuracy_max  Accuracy_min   F_score  
        # Ranking                                        
        # 0                 1.0           0.3  0.230769  
        # 1                 1.0           0.3  0.230769  
        # 3                 1.0           0.3  0.230769  
        # 4                 1.0           0.3  0.230769  
        # 2                 0.5           0.3  0.230769 
        summary = pd.concat([pd.DataFrame(self.acc.keys()),pd.DataFrame(map(lambda x: statistics.mean(self.acc[x]), self.acc)),\
                            pd.DataFrame(map(lambda x: statistics.stdev(self.acc[x]), self.acc)),\
                            pd.DataFrame(map(lambda x: max(self.acc[x]), self.acc)),\
                            pd.DataFrame(map(lambda x: min(self.acc[x]), self.acc)),\
                            pd.DataFrame(map(lambda x: statistics.mean(self.fscore[x]), self.fscore))],axis=1)
        summary.columns = ['Estimator','Accuracy_mean','Accuracy_std','Accuracy_max','Accuracy_min','F_score']
        summary.index.rename('Ranking', inplace=True)
        
        return summary.sort_values(by = [sort_by], ascending=False)
                  
def run_pipline(models, model_grid_params, data_2014_up, latest_sec=30, pred_sec=10, day=1):
    # Use Model_Selection class, define an object of the class called pip
    # run pipline() method
    # return pip
    data_2014 = data_2014_up
    pip = Model_Selection(models,model_grid_params,data_2014,latest_sec,pred_sec,day)
    pip.pipline()
    return pip

class test_Model_Selection(unittest.TestCase):
    def setUp(self):
        self.models = {
        'RandomForestClassifier': RandomForestClassifier(random_state = 0),
        'ExtraTreesClassifier': ExtraTreesClassifier(random_state = 0),
        'AdaBoostClassifier': AdaBoostClassifier(base_estimator = DecisionTreeClassifier(),\
                                                 n_estimators = 10,random_state = 0),
        'GradientBoostingClassifier': GradientBoostingClassifier(random_state = 0),
        'SVC': SVC(probability=True,random_state = 0),
        }
        self.model_grid_params = {
        'RandomForestClassifier': {'max_features':[None],'n_estimators':[10],'max_depth':[10],\
                                   'min_samples_split':[2],'criterion':['entropy'],\
                                   'min_samples_leaf':[3]},
        'ExtraTreesClassifier': {'max_features':[None],'n_estimators':[10],'max_depth':[10],\
                                 'min_samples_split':[2],'criterion':['entropy'],\
                                 'min_samples_leaf':[3]},
        'AdaBoostClassifier': {"base_estimator__criterion" : ["entropy"],\
                               "base_estimator__max_depth": [None],\
                               "base_estimator__min_samples_leaf" : [3],\
                               "base_estimator__min_samples_split" : [2],\
                               "base_estimator__max_features" : [None]},
        'GradientBoostingClassifier': {'max_features':[None],'n_estimators':[10],'max_depth':[10],\
                                       'min_samples_split':[2],'min_samples_leaf':[3],\
                                       'learning_rate':[0.1],'subsample':[1.0]},
        'SVC': [{'kernel':['rbf'],'gamma':[1e-1],'C':[1]},\
                {'kernel':['linear'],'C':[1,10]}]
        }
        self.data = []
        self.data.append(pd.read_csv(io.StringIO(data_string)))
        self.latest_sec = 30
        self.pred_sec = 10
        self.day = 1
    
    def test1(self):
        pip = Model_Selection(self.models, self.model_grid_params, self.data, self.latest_sec, self.pred_sec, self.day)
        if pip.grid == {}:
            print('test1: pass')
        else:
            print('test1: failed')

    def test2(self):
        pip = Model_Selection(self.models, self.model_grid_params, self.data, self.latest_sec, self.pred_sec, self.day)
        if pip.true_values_day == {}:
            print('test2: pass')
        else:
            print('test2: failed')
    
    def test3(self):
        pip = run_pipline(self.models, self.model_grid_params, self.data)
        self.assertEqual(list(pip.summary_day[0].columns), ['Estimator', 'Accuracy_mean', 'Accuracy_std', 'Accuracy_max', 'Accuracy_min', 'F_score'])
    
    def test4(self):
        pip = run_pipline(self.models, self.model_grid_params, self.data)
        print(pip.summary_day[0]['Estimator'])

if __name__ == '__main__':
    tmp = test_Model_Selection()
    tmp.setUp()
    func_name = input().strip()
    tmp.__getattribute__(func_name)()