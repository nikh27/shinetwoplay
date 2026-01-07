from django.shortcuts import render, redirect
import random
import string

# Generate room code
def generate_code(length=4):
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(length))

def home(request):
    return render(request, "home.html")

def create_room(request):
    name = request.GET.get("name", "Guest")
    code = generate_code()
    return redirect(f"/rooms/{code}/?name={name}")

def room_page(request, code):
    name = request.GET.get("name", "")

    if not name:
        return redirect("/")

    return render(request, "room.html", {
        "room": code,
        "username": name
    })