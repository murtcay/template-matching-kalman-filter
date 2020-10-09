import os
import cv2
import numpy as np
import sys
import time
class KalmanFilter:
    kf = cv2.KalmanFilter(4,2)
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
    kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
    def Estimate(self, coordX, coordY):
        ''' This function estimates the position of the object '''
        measured = np.array([[np.float32(coordX)], [np.float32(coordY)]])
        self.kf.correct(measured)
        predicted = self.kf.predict()
        return predicted
class TemplateMatch:
    def __init__(self,kalmanFilterEnable=False, match_method = cv2.TM_CCORR_NORMED, threshold=0.7):
        ''' This function initializes the Template Matching Class '''
        self.source_video = ""
        self.cam = cv2.VideoCapture()
        self.kalmanFilterEnable = kalmanFilterEnable
        self.threshold = threshold
        self.match_method = match_method
        self.track_mode = "manual"
    def detect(self, frame, templ, w, h):
        ''' This function detects the template on source frame'''
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        match_result = cv2.matchTemplate(gray_frame, templ, self.match_method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match_result)
        if self.match_method == cv2.TM_SQDIFF or self.match_method == cv2.TM_SQDIFF_NORMED:
            top_left = min_loc
            match_val = min_val
        else:
            top_left = max_loc
            match_val = max_val
        return (match_val, top_left[0], top_left[1])
    def main(self):
        ok = self.cam.open(self.source_video)
        if not ok:
            print(". Error - could not open video file")
            return -1
        numOfFrames = int(self.cam.get(cv2.CAP_PROP_FRAME_COUNT))
        if 0 >= numOfFrames:
            print(". Error - could not read video file")
            return -1
        ok, frame = self.cam.read()
        if not ok:
            print(". Error - video frame could not read")
            return -1
        myRoi = cv2.selectROI("Tracking", frame, True, True)
        imCrop = frame[int(myRoi[1]) : int(myRoi[1]+myRoi[3]) , int(myRoi[0]) : int(myRoi[0]+myRoi[2])]
        template_gray = cv2.cvtColor(imCrop, cv2.COLOR_BGR2GRAY)
        template = (template_gray, template_gray.shape[::-1])
        kalmanFilter = KalmanFilter()
        predictedResults = np.zeros((2,1), np.float32)
        camWidth= int(self.cam.get(3))
        camHeight = int(self.cam.get(4))
        searchBound = [0, 0, camWidth, camHeight]
        templateLocation = [0, 0, camWidth, camHeight]
        frame_count = 0
        keyInput = 0
        predictedCoordX = 0
        predictedCoordy = 0
        displayControl = True
        self.cam.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        while True:
            ok, frame = self.cam.read()
            if not ok:
                print(". Error - video frame could not read")
                break
            tw = int(template[1][0])
            th = int(template[1][1])
            areaToScan = frame[searchBound[1]:searchBound[3], searchBound[0]:searchBound[2]]
            matchedValue, differenceX, differenceY = self.detect(areaToScan, template[0], *template[1])
            templateLocation[0] = differenceX + searchBound[0]
            templateLocation[1] = differenceY + searchBound[1]
            templateLocation[2] = differenceX + searchBound[0] + tw
            templateLocation[3] = differenceY + searchBound[1] + th
            if matchedValue >= self.threshold and self.kalmanFilterEnable:
                templateLocationCpy = templateLocation
                predictedResults = kalmanFilter.Estimate(templateLocation[0], templateLocation[1])
                predictedCoordX, predictedCoordY, cov_x, cov_y = predictedResults[:,0]
                if round(abs(cov_x)) < 10 and 0 < round(abs(cov_x)):
                    templateLocationCpy[0] = predictedCoordX
                    templateLocationCpy[2] = predictedCoordX + tw
                    x_margin = np.sqrt((np.square(matchedValue*cov_x)+np.square((1-matchedValue)*differenceX))/ 2)+5
                else:
                    x_margin = np.sqrt((np.square((1-matchedValue)*(predictedCoordX-templateLocation[0]))+np.square(matchedValue*differenceX))/2) + 10
                if round(abs(cov_y)) < 10 and 0 < round(abs(cov_y)):
                    templateLocationCpy[1] = predictedCoordY
                    templateLocationCpy[3] = predictedCoordY + th
                    y_margin = np.sqrt((np.square(matchedValue*cov_y)+np.square((1-matchedValue)*differenceY))/ 2)+5
                else:
                    y_margin = np.sqrt((np.square((1-matchedValue)*(predictedCoordY-templateLocation[1]))+np.square(matchedValue*differenceY))/2) + 10 
                searchBound[0] = int(abs(templateLocationCpy[0] - x_margin))
                searchBound[1] = int(abs(templateLocationCpy[1] - y_margin))
                searchBound[2] = int(abs(templateLocationCpy[2] + x_margin))
                searchBound[3] = int(abs(templateLocationCpy[3] + y_margin))
                if searchBound[0] < 0:
                    searchBound[0] = 0
                if searchBound[1] <= 0:
                    searchBound[1] = 0
                if searchBound[2]>= camWidth:
                    searchBound[2] = camWidth
                if searchBound[3] >= camHeight:
                    searchBound[3] = camHeight
                displayControl = True
            else:
                searchBound = [0, 0, camWidth, camHeight]
                myRoi = cv2.selectROI("Tracking", frame, True, True)
                imCrop = frame[int(myRoi[1]) : int(myRoi[1]+myRoi[3]) , int(myRoi[0]) : int(myRoi[0]+myRoi[2])]
                template_gray = cv2.cvtColor(imCrop, cv2.COLOR_BGR2GRAY)
                template = (template_gray, template_gray.shape[::-1])
                displayControl = False
            if displayControl:
                cv2.rectangle(frame, (int(templateLocation[0]), int(templateLocation[1])), (int(templateLocation[0]+tw), int(templateLocation[1]+th)), (255,0,0), 0)
                cv2.imshow("Tracking", frame)
            print("frame num: ", frame_count, " match: ", matchedValue)
            frame_count += 1
            keyInput = (cv2.waitKey(1) & 0xFF)
            if keyInput == 27:
                break
        cv2.destroyAllWindows()
if __name__ == "__main__":
    app = TemplateMatch()
    app.source_video = "../template_matching_v1/videos/fish5_trial1_055hz_01cm.mov"
    app.kalmanFilterEnable = True
    app.threshold = 0.9999
    app.main()
    print("=========== DONE =============")