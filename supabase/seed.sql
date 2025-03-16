-- Sample data for MeatWise database

-- Sample ingredients
INSERT INTO ingredients (name, description, category, risk_level, concerns, alternatives)
VALUES
  ('Sodium Nitrite', 'A preservative commonly used in processed meats', 'preservative', 'high', 
   ARRAY['Cancer risk', 'Blood vessel damage'], 
   ARRAY['Celery powder', 'Cherry powder', 'Vitamin C']),
  
  ('Monosodium Glutamate (MSG)', 'Flavor enhancer commonly used in processed foods', 'flavor enhancer', 'medium', 
   ARRAY['Headaches', 'Flushing', 'Sweating'], 
   ARRAY['Yeast extract', 'Tomatoes', 'Mushrooms']),
  
  ('Sodium Phosphate', 'Used to retain moisture in processed meats', 'stabilizer', 'medium', 
   ARRAY['Kidney damage', 'Heart issues'], 
   ARRAY['Potassium phosphate', 'Natural brines']),
  
  ('BHA (Butylated hydroxyanisole)', 'Synthetic antioxidant used as a preservative', 'preservative', 'high', 
   ARRAY['Potential carcinogen', 'Endocrine disruptor'], 
   ARRAY['Vitamin E', 'Rosemary extract']),
  
  ('Sodium Erythorbate', 'Preservative used to prevent color change in meat', 'preservative', 'low', 
   ARRAY['Gastrointestinal discomfort'], 
   ARRAY['Vitamin C', 'Citric acid']);

-- Sample products
INSERT INTO products (code, name, brand, description, ingredients_text, ingredients_array, 
                     calories, protein, fat, carbohydrates, salt, meat_type,
                     contains_nitrites, contains_phosphates, contains_preservatives,
                     antibiotic_free, hormone_free, pasture_raised,
                     risk_rating, risk_score, image_url)
VALUES
  ('1234567890123', 'Premium Bacon', 'MeatCo', 'Sliced bacon from pasture-raised pigs', 
   'Pork, water, salt, sodium phosphate, sodium erythorbate, sodium nitrite', 
   ARRAY['Pork', 'water', 'salt', 'sodium phosphate', 'sodium erythorbate', 'sodium nitrite'],
   541, 37, 42, 1.4, 1.8, 'pork',
   TRUE, TRUE, TRUE,
   FALSE, FALSE, TRUE,
   'Yellow', 50, 'https://example.com/images/bacon.jpg'),
  
  ('2345678901234', 'Organic Chicken Breast', 'FarmFresh', 'Organic chicken breast from free-range chickens', 
   'Chicken breast', 
   ARRAY['Chicken breast'],
   165, 31, 3.6, 0, 0.1, 'chicken',
   FALSE, FALSE, FALSE,
   TRUE, TRUE, TRUE,
   'Green', 10, 'https://example.com/images/chicken.jpg'),
  
  ('3456789012345', 'Beef Hot Dogs', 'MeatCo', 'Classic beef hot dogs', 
   'Beef, water, salt, corn syrup, sodium phosphate, sodium nitrite, BHA, MSG', 
   ARRAY['Beef', 'water', 'salt', 'corn syrup', 'sodium phosphate', 'sodium nitrite', 'BHA', 'MSG'],
   290, 12, 26, 2, 1.1, 'beef',
   TRUE, TRUE, TRUE,
   FALSE, FALSE, FALSE,
   'Red', 80, 'https://example.com/images/hotdogs.jpg'),
  
  ('4567890123456', 'Grass-Fed Ground Beef', 'GreenPastures', 'Ground beef from grass-fed cattle', 
   'Grass-fed beef', 
   ARRAY['Grass-fed beef'],
   250, 26, 17, 0, 0.1, 'beef',
   FALSE, FALSE, FALSE,
   TRUE, TRUE, TRUE,
   'Green', 5, 'https://example.com/images/groundbeef.jpg'),
  
  ('5678901234567', 'Turkey Deli Slices', 'DailyDeli', 'Sliced turkey breast for sandwiches', 
   'Turkey breast, water, salt, modified food starch, sodium phosphate, sodium nitrite', 
   ARRAY['Turkey breast', 'water', 'salt', 'modified food starch', 'sodium phosphate', 'sodium nitrite'],
   100, 15, 2, 3, 1.2, 'turkey',
   TRUE, TRUE, FALSE,
   FALSE, FALSE, FALSE,
   'Yellow', 45, 'https://example.com/images/turkey.jpg');

-- Link products to ingredients
INSERT INTO product_ingredients (product_code, ingredient_id, position)
VALUES
  ('1234567890123', (SELECT id FROM ingredients WHERE name = 'Sodium Nitrite'), 6),
  ('1234567890123', (SELECT id FROM ingredients WHERE name = 'Sodium Phosphate'), 4),
  ('1234567890123', (SELECT id FROM ingredients WHERE name = 'Sodium Erythorbate'), 5),
  
  ('3456789012345', (SELECT id FROM ingredients WHERE name = 'Sodium Nitrite'), 6),
  ('3456789012345', (SELECT id FROM ingredients WHERE name = 'Sodium Phosphate'), 5),
  ('3456789012345', (SELECT id FROM ingredients WHERE name = 'BHA (Butylated hydroxyanisole)'), 7),
  ('3456789012345', (SELECT id FROM ingredients WHERE name = 'Monosodium Glutamate (MSG)'), 8),
  
  ('5678901234567', (SELECT id FROM ingredients WHERE name = 'Sodium Nitrite'), 6),
  ('5678901234567', (SELECT id FROM ingredients WHERE name = 'Sodium Phosphate'), 5);

-- Add alternative product suggestions
INSERT INTO product_alternatives (product_code, alternative_code, similarity_score, reason)
VALUES
  ('1234567890123', '4567890123456', 0.7, 'Lower in preservatives and additives'),
  ('3456789012345', '2345678901234', 0.5, 'No preservatives or additives'),
  ('5678901234567', '2345678901234', 0.6, 'No nitrites or phosphates'); 