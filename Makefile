.PHONY: setup generate-data start-simulator train-models start-dashboard docker-up docker-down test clean

setup:
	pip install -r requirements.txt

generate-data:
	python simulator/historical_generator.py

start-simulator:
	python simulator/traffic_generator.py

train-models:
	python ml/train.py

start-dashboard:
	streamlit run dashboard/Home.py

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

test:
	python -m unittest discover -s tests

clean:
	rm -rf __pycache__ */__pycache__ *.log logs/*.log ml/models/*.joblib ml/models/*.json
