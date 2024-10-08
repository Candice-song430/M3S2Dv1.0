#
#  The original implementation was written by Michael Dorner.
#      https://github.com/michaeldorner/DecisionTrees
#
#
#
import csv
from collections import defaultdict

import numpy
# import pydotplus

#
# https://github.com/michaeldorner/DecisionTrees
# http://www.math.uah.edu/stat/data/Fisher.csv
import xlrd


class CART:
    """Binary tree implementation with true and false branch. """

    def __init__(self, col=-1, value=None, trueBranch=None, falseBranch=None, results=None, summary=None):
        self.col = col
        self.value = value
        self.trueBranch = trueBranch
        self.falseBranch = falseBranch
        self.results = results  # None for nodes, not None for leaves
        self.summary = summary


def divideSet(rows, column, value):
    splittingFunction = None
    if isinstance(value, int) or isinstance(value, float):  # for int and float values
        splittingFunction = lambda row: row[column] >= value
    else:  # for strings
        splittingFunction = lambda row: row[column] == value
    list1 = [row for row in rows if splittingFunction(row)]
    list2 = [row for row in rows if not splittingFunction(row)]
    return (list1, list2)


def uniqueCounts(rows):
    results = {}
    for row in rows:
        # response variable is in the last column
        r = row[-1]
        if r not in results: results[r] = 0
        results[r] += 1
    return results


def entropy(rows):
    from math import log
    log2 = lambda x: log(x) / log(2)
    results = uniqueCounts(rows)

    entr = 0.0
    for r in results:
        p = float(results[r]) / len(rows)
        entr -= p * log2(p)
    return entr


def gini(rows):
    total = len(rows)
    counts = uniqueCounts(rows)
    imp = 0.0

    for k1 in counts:
        p1 = float(counts[k1]) / total
        for k2 in counts:
            if k1 == k2: continue
            p2 = float(counts[k2]) / total
            imp += p1 * p2
    return imp


def variance(rows):
    if len(rows) == 0: return 0
    data = [float(row[len(row) - 1]) for row in rows]
    mean = sum(data) / len(data)

    variance = sum([(d - mean) ** 2 for d in data]) / len(data)
    return variance


labels = {}


def growDecisionTreeFrom(rows, evaluationFunction=gini):
    """Grows and then returns a binary decision tree.
    evaluationFunction: entropy or gini"""

    if len(rows) == 0:
        return CART()

    currentScore = evaluationFunction(rows)

    bestGain = 0.0
    bestAttribute = None
    bestSets = None

    columnCount = len(rows[0]) - 1  # last column is the result/target column

    for col in range(0, columnCount):
        columnValues = [row[col] for row in rows]

        # unique values
        lsUnique = list(set(columnValues))

        for value in lsUnique:
            (set1, set2) = divideSet(rows, col, value)

            # Gain -- Entropy or Gini
            p = float(len(set1)) / len(rows)
            gain = currentScore - p * evaluationFunction(set1) - (1 - p) * evaluationFunction(set2)
            if gain > bestGain and len(set1) > 0 and len(set2) > 0:
                bestGain = gain
                bestAttribute = (col, value)
                bestSets = (set1, set2)

    dcY = {'impurity': '%.3f' % currentScore, 'samples': '%d' % len(rows)}
    if bestGain > 0:
        trueBranch = growDecisionTreeFrom(bestSets[0], evaluationFunction)
        falseBranch = growDecisionTreeFrom(bestSets[1], evaluationFunction)
        return CART(col=bestAttribute[0], value=bestAttribute[1], trueBranch=trueBranch,
                    falseBranch=falseBranch, summary=dcY)
    else:
        return CART(results=uniqueCounts(rows), summary=dcY)


def CART_prune(tree, minGain, evaluationFunction=entropy, notify=False):
    """Prunes the obtained tree according to the minimal gain (entropy or Gini). """
    # recursive call for each branch
    if tree.trueBranch.results == None: CART_prune(tree.trueBranch, minGain, evaluationFunction, notify)
    if tree.falseBranch.results == None: CART_prune(tree.falseBranch, minGain, evaluationFunction, notify)

    # merge leaves (potentionally)
    if tree.trueBranch.results != None and tree.falseBranch.results != None:
        tb, fb = [], []

        for v, c in tree.trueBranch.results.items(): tb += [[v]] * c
        for v, c in tree.falseBranch.results.items(): fb += [[v]] * c

        p = float(len(tb)) / len(tb + fb)
        delta = evaluationFunction(tb + fb) - p * evaluationFunction(tb) - (1 - p) * evaluationFunction(fb)
        if delta < minGain:
            if notify: print('A branch was pruned: gain = %f' % delta)
            tree.trueBranch, tree.falseBranch = None, None
            tree.results = uniqueCounts(tb + fb)


def classify(observations, tree, dataMissing=False):
    """Classifies the observationss according to the tree.
    dataMissing: true or false if data are missing or not. """

    def classifyWithoutMissingData(observations, tree):
        if tree.results != None:  # leaf
            return tree.results
        else:
            v = observations[tree.col]
            branch = None
            if isinstance(v, int) or isinstance(v, float):
                if v >= tree.value:
                    branch = tree.trueBranch
                else:
                    branch = tree.falseBranch
            else:
                if v == tree.value:
                    branch = tree.trueBranch
                else:
                    branch = tree.falseBranch
        return classifyWithoutMissingData(observations, branch)

    def classifyWithMissingData(observations, tree):
        if tree.results != None:  # leaf
            return tree.results
        else:
            v = observations[tree.col]
            if v == None:
                tr = classifyWithMissingData(observations, tree.trueBranch)
                fr = classifyWithMissingData(observations, tree.falseBranch)
                tcount = sum(tr.values())
                fcount = sum(fr.values())
                tw = float(tcount) / (tcount + fcount)
                fw = float(fcount) / (tcount + fcount)
                result = defaultdict(int)
                for k, v in tr.items(): result[k] += v * tw
                for k, v in fr.items(): result[k] += v * fw
                return dict(result)
            else:
                branch = None
                if isinstance(v, int) or isinstance(v, float):
                    if v >= tree.value:
                        branch = tree.trueBranch
                    else:
                        branch = tree.falseBranch
                else:
                    if v == tree.value:
                        branch = tree.trueBranch
                    else:
                        branch = tree.falseBranch
            return classifyWithMissingData(observations, branch)

    # function body
    if dataMissing:
        return classifyWithMissingData(observations, tree)
    else:
        return classifyWithoutMissingData(observations, tree)


def CART_plot(decisionTree):
    """Plots the obtained decision tree. """

    def toString(decisionTree, indent=''):
        if decisionTree.results != None:  # leaf node
            dictTree = {}
            lsX = [(x, y) for x, y in decisionTree.results.items()]
            lsX.sort(reverse=True)
            szY = ', '.join(['%s: %s' % (x, y) for x, y in lsX])
            for x, y in lsX:
                dictTree[str(x)] = str(y)
            return szY, dictTree
        else:
            szCol = 'Column %s' % decisionTree.col
            dictTree = {}
            if szCol in labels:
                szCol = labels[szCol]
                dictTree[szCol] = {}
            if isinstance(decisionTree.value, int) or isinstance(decisionTree.value, float):
                decision = '%s >= %s?' % (szCol, decisionTree.value)
            else:
                decision = '%s == %s?' % (szCol, decisionTree.value)
            dictTree[szCol] = {decisionTree.value: {'Yes': None, 'No': None}}
            trueBranchString, trueBranchDict = toString(decisionTree.trueBranch, indent + '\t\t')
            dictTree[szCol][decisionTree.value]['Yes'] = trueBranchDict
            trueBranch = indent + 'yes -> ' + trueBranchString

            falseBranchString, falseBranchDict = toString(decisionTree.falseBranch, indent + '\t\t')
            dictTree[szCol][decisionTree.value]['No'] = falseBranchDict
            falseBranch = indent + 'no  -> ' + falseBranchString
            return (decision + '\n' + trueBranch + '\n' + falseBranch), dictTree

    stringTree, dictTree = toString(decisionTree)
    # print(stringTree)
    return dictTree


def dotgraph(decisionTree):
    global labels
    dcNodes = defaultdict(list)
    """Plots the obtained decision tree. """

    def toString(iSplit, decisionTree, bBranch, szParent="null", indent=''):
        if decisionTree.results != None:  # leaf node
            lsX = [(x, y) for x, y in decisionTree.results.items()]
            lsX.sort(reverse=True)
            szY = ', '.join(['%s: %s' % (x, y) for x, y in lsX])
            dcY = {"name": szY, "parent": szParent}
            dcSummary = decisionTree.summary
            dcNodes[iSplit].append(['leaf', dcY['name'], szParent, bBranch, dcSummary['impurity'],
                                    dcSummary['samples']])
            return dcY
        else:
            szCol = 'Column %s' % decisionTree.col
            if szCol in labels:
                szCol = labels[szCol]
            if isinstance(decisionTree.value, int) or isinstance(decisionTree.value, float):
                decision = '%s >= %s' % (szCol, decisionTree.value)
            else:
                decision = '%s == %s' % (szCol, decisionTree.value)
            trueBranch = toString(iSplit + 1, decisionTree.trueBranch, True, decision, indent + '\t\t')
            falseBranch = toString(iSplit + 1, decisionTree.falseBranch, False, decision, indent + '\t\t')
            dcSummary = decisionTree.summary
            dcNodes[iSplit].append([iSplit + 1, decision, szParent, bBranch, dcSummary['impurity'],
                                    dcSummary['samples']])
            return

    toString(0, decisionTree, None)
    lsDot = ['digraph Tree {',
             'node [shape=box, style="filled, rounded", color="black", fontname=helvetica] ;',
             'edge [fontname=helvetica] ;'
             ]
    i_node = 0
    dcParent = {}
    for nSplit in range(len(dcNodes)):
        lsY = dcNodes[nSplit]
        for lsX in lsY:
            iSplit, decision, szParent, bBranch, szImpurity, szSamples = lsX
            if type(iSplit) == int:
                szSplit = '%d-%s' % (iSplit, decision)
                dcParent[szSplit] = i_node
                lsDot.append('%d [label=<%s<br/>impurity %s<br/>samples %s>, fillcolor="#e5813900"] ;' % (i_node,
                                                                                                          decision.replace(
                                                                                                              '>=',
                                                                                                              '&ge;').replace(
                                                                                                              '?', ''),
                                                                                                          szImpurity,
                                                                                                          szSamples))
            else:
                lsDot.append('%d [label=<impurity %s<br/>samples %s<br/>class %s>, fillcolor="#e5813900"] ;' % (i_node,
                                                                                                                szImpurity,
                                                                                                                szSamples,
                                                                                                                decision))

            if szParent != 'null':
                if bBranch:
                    szAngle = '45'
                    szHeadLabel = 'True'
                else:
                    szAngle = '-45'
                    szHeadLabel = 'False'
                szSplit = '%d-%s' % (nSplit, szParent)
                p_node = dcParent[szSplit]
                if nSplit == 1:
                    lsDot.append('%d -> %d [labeldistance=2.5, labelangle=%s, headlabel="%s"] ;' % (p_node,
                                                                                                    i_node, szAngle,
                                                                                                    szHeadLabel))
                else:
                    lsDot.append('%d -> %d ;' % (p_node, i_node))
            i_node += 1
    lsDot.append('}')
    dot_data = '\n'.join(lsDot)
    return dot_data


def loadXLS(file):
    """Loads a CSV file and converts all floats and ints into basic datatypes."""

    def convertTypes(s):
        if isinstance(s, str):
            s = s.strip()
            try:
                return float(s) if '.' in s else int(s)
            except ValueError:
                return s
        return s

    data = []
    wb = xlrd.open_workbook(file)
    table = wb.sheets()[0]
    row = table.nrows
    for i in range(row):
        data.append(table.row_values(i))

    lsHeader = data[0]
    for i, szY in enumerate(lsHeader):
        szCol = 'Column %d' % i
        labels[szCol] = str(szY)
    data.pop(0)

    return labels, [[convertTypes(item) for item in row] for row in data]


def CART_test(file, decisionTree, args):
    labels, oriTestData = loadXLS(file)  # demo data from matlab
    # oriTestData = oriTestData[2000:]
    columnCount = len(oriTestData[0]) - 1  # last column is the result/target column
    actualClass = [row[columnCount] for row in oriTestData]
    testData = numpy.delete(oriTestData, columnCount, axis=1)
    correctNum = 0
    wrongNum = 0
    for i, row in enumerate(testData):
        predict = classify(row, decisionTree)
        if actualClass[i] in predict.keys():
            correctNum += 1
        else:
            wrongNum += 1
    totalNum = len(oriTestData)
    data = [
        'Attribute selection metric: Gini coefficient 0.8',
        'Number of test cases: ' + str(totalNum),
        'Number of correct examples: ' + str(correctNum),
        'Number of incorrect examples: ' + str(wrongNum),
        'Accuracy: ' + str('{:.2%}'.format(correctNum / totalNum))
    ]  # 测试分析的结果

    return data

# if __name__ == '__main__':
    # Select the example you want to classify

    # All examples do the following steps:
    #   1. Load training data
    #   2. Let the decision tree grow
    #   4. Plot the decision tree
    #   5. classify without missing data
    #   6. Classifiy with missing data
    #   (7.) Prune the decision tree according to a minimal gain level
    #   (8.) Plot the pruned tree

