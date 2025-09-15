from LittleLemonAPI.models import Category, MenuItem

def run():
    # Delete all existing data to start fresh
    MenuItem.objects.all().delete()
    Category.objects.all().delete()
    
    # Create categories
    starters = Category.objects.create(title="Starters", slug="starters")
    main_courses = Category.objects.create(title="Main Courses", slug="main-courses")
    desserts = Category.objects.create(title="Desserts", slug="desserts")

    # Create menu items and link them to categories
    MenuItem.objects.create(title="Bruschetta", price=8.50, featured=False, category=starters)
    MenuItem.objects.create(title="Greek Salad", price=12.00, featured=False, category=starters)
    MenuItem.objects.create(title="Moussaka", price=24.50, featured=True, category=main_courses)
    MenuItem.objects.create(title="Lasagna", price=18.00, featured=False, category=main_courses)
    MenuItem.objects.create(title="Tiramisu", price=10.50, featured=True, category=desserts)
    MenuItem.objects.create(title="Baklava", price=9.00, featured=False, category=desserts)

    print("Database populated with sample menu items!")