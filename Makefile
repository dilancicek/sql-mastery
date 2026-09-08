.PHONY: up down seed

up:
		docker compose up -d

down:
		docker compose down -v

seed:
	@echo "Veriler Python ile uretiliyor..."
	uv run scripts/generate_data.py
	@echo "Veriler veritabanina aktariliyor..."
	docker exec ecommerce_db psql -U admin -d ecommerce -c "COPY users FROM '/data/users.csv' DELIMITER ',' CSV HEADER NULL '';"
	docker exec ecommerce_db psql -U admin -d ecommerce -c "COPY categories FROM '/data/categories.csv' DELIMITER ',' CSV HEADER NULL '';"
	docker exec ecommerce_db psql -U admin -d ecommerce -c "COPY products FROM '/data/products.csv' DELIMITER ',' CSV HEADER NULL '';"
	docker exec ecommerce_db psql -U admin -d ecommerce -c "COPY orders FROM '/data/orders.csv' DELIMITER ',' CSV HEADER NULL '';"
	docker exec ecommerce_db psql -U admin -d ecommerce -c "COPY order_items FROM '/data/order_items.csv' DELIMITER ',' CSV HEADER NULL '';"
	@echo "Islem tamam! Veritabani hazir."