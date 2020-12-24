def F_s(SL, threshold):
    return sum([(max(threshold - sl*100, 0))**2 for sl in SL.values()])