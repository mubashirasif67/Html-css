#!/usr/bin/env python
"""
Generate synthetic receipt images for OCR testing
"""

import os
import random
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import numpy as np

def generate_receipt(receipt_id, amount, donation_type="General"):
    """Generate a synthetic receipt image"""
    
    # Create white background
    width, height = 600, 800
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a better font, fallback to default
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 36)
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 24)
        font_body = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
    except:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
    
    # Add some noise/texture
    noise = np.random.randint(240, 255, (height, width, 3), dtype=np.uint8)
    noise_img = Image.fromarray(noise)
    img = Image.blend(img, noise_img, 0.1)
    draw = ImageDraw.Draw(img)
    
    # Receipt content
    y_pos = 50
    
    # Header
    draw.text((width//2 - 150, y_pos), "BLESSINGS FOUNDATION", font=font_title, fill='black')
    y_pos += 60
    
    draw.text((width//2 - 100, y_pos), "DONATION RECEIPT", font=font_header, fill='black')
    y_pos += 50
    
    # Line separator
    draw.line([(50, y_pos), (width-50, y_pos)], fill='black', width=2)
    y_pos += 30
    
    # Receipt details
    date = datetime.now() - timedelta(days=random.randint(0, 30))
    
    details = [
        f"Receipt No: RCP-{receipt_id:06d}",
        f"Date: {date.strftime('%B %d, %Y')}",
        f"Time: {date.strftime('%I:%M %p')}",
        "",
        f"Donation Type: {donation_type}",
        f"Payment Method: {random.choice(['Cash', 'Bank Transfer', 'Online'])}",
        "",
        "="*40,
    ]
    
    for line in details:
        draw.text((60, y_pos), line, font=font_body, fill='black')
        y_pos += 35
    
    # Amount (main focus for OCR)
    amount_formats = [
        f"Amount: PKR {amount:,}",
        f"Amount: Rs. {amount:,}",
        f"Total: ₨ {amount:,}",
        f"Received: PKR {amount:,.2f}",
    ]
    
    amount_text = random.choice(amount_formats)
    draw.text((60, y_pos), amount_text, font=font_header, fill='black')
    y_pos += 50
    
    draw.text((60, y_pos), "="*40, font=font_body, fill='black')
    y_pos += 40
    
    # Footer
    footer_lines = [
        "Thank you for your generous donation!",
        "Your contribution makes a difference.",
        "",
        "Blessings Foundation",
        "www.blessings.org | info@blessings.org",
        "Tel: +92-300-1234567"
    ]
    
    for line in footer_lines:
        draw.text((60, y_pos), line, font=font_body, fill='gray')
        y_pos += 30
    
    # Add some realistic imperfections
    # Slight rotation
    angle = random.uniform(-2, 2)
    img = img.rotate(angle, fillcolor='white', expand=True)
    
    # Add some blur
    if random.random() > 0.5:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.0)))
    
    # Add some spots/marks
    draw = ImageDraw.Draw(img)
    for _ in range(random.randint(3, 10)):
        x = random.randint(0, width)
        y = random.randint(0, height)
        radius = random.randint(1, 3)
        gray_level = random.randint(200, 240)
        draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                    fill=(gray_level, gray_level, gray_level))
    
    return img


def main():
    """Generate multiple synthetic receipts"""
    
    output_dir = "/app/uploads/synthetic_receipts"
    os.makedirs(output_dir, exist_ok=True)
    
    # Common donation amounts
    amounts = [500, 1000, 2000, 2500, 5000, 7500, 10000, 15000, 20000, 25000, 50000, 100000]
    donation_types = ["Zakat", "Sadaqah", "General", "Fitrana", "Qurbani"]
    
    num_receipts = 50
    
    print(f"Generating {num_receipts} synthetic receipts...")
    
    for i in range(num_receipts):
        amount = random.choice(amounts)
        donation_type = random.choice(donation_types)
        
        receipt = generate_receipt(i+1, amount, donation_type)
        
        filename = f"receipt_{i+1:04d}_{amount}.png"
        filepath = os.path.join(output_dir, filename)
        
        receipt.save(filepath)
        print(f"Generated: {filename}")
    
    print(f"\n✅ Generated {num_receipts} receipts in {output_dir}")
    
    # Generate a test set with known amounts for accuracy testing
    test_amounts = [1000, 5000, 10000, 25000, 50000]
    test_dir = os.path.join(output_dir, "test_set")
    os.makedirs(test_dir, exist_ok=True)
    
    print("\nGenerating test set with known amounts...")
    
    for i, amount in enumerate(test_amounts):
        for j in range(3):  # 3 variations of each amount
            receipt = generate_receipt(f"TEST{i:02d}{j:02d}", amount, "Test")
            filename = f"test_receipt_amount_{amount}_{j+1}.png"
            filepath = os.path.join(test_dir, filename)
            receipt.save(filepath)
            print(f"Generated test receipt: {filename}")
    
    # Create a manifest file
    manifest_path = os.path.join(test_dir, "manifest.txt")
    with open(manifest_path, "w") as f:
        f.write("Test Receipt Manifest\n")
        f.write("=" * 30 + "\n")
        for amount in test_amounts:
            for j in range(3):
                f.write(f"test_receipt_amount_{amount}_{j+1}.png: PKR {amount}\n")
    
    print(f"\n✅ Test set generated in {test_dir}")
    print(f"📄 Manifest saved to {manifest_path}")


if __name__ == "__main__":
    main()