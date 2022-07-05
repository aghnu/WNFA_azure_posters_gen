import joblib 
import os

model_path = os.path.abspath(os.path.split(__file__)[0] + "/" + "models/emotion_classifier_pipe.pkl")
pipe = joblib.load(open(model_path,"rb"))

def predict_emo_raw(text):
	classes = pipe.classes_
	results = pipe.predict_proba([text])
	results_dict = dict()
	for index in range(len(classes)):
		results_dict[classes[index]] = results[0][index]

	results_dict['happiness'] = abs(results_dict['surprise'] - results_dict['joy']) * 1.2
	return results_dict

def predict_emo(text):
	results_dict = predict_emo_raw(text)

	# add happiness
	results_dict['happiness'] = abs(results_dict['surprise'] - results_dict['joy']) * 1.2

	# apply weights to different emotions
	EMO_WEIGHTS = {
		'anger': 		1.1,
		'disgust':		1,
		'fear':			1,
		'joy':			0.75,
		'neutral':		0.85,
		'sadness':		1,
		'shame':		1,
		'surprise':		1.1,
		'happiness':	1,
	}

	for emo in EMO_WEIGHTS:
		results_dict[emo] = results_dict[emo] * EMO_WEIGHTS[emo]

	return results_dict