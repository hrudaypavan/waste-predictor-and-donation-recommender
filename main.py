from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/register", response_class=HTMLResponse)
def register_form():
    return """
    <h2>Register</h2>
    <form method="post" action="/register">
        <input type="text" name="username" placeholder="Username"><br><br>
        <input type="password" name="password" placeholder="Password"><br><br>
        <button type="submit">Register</button>
    </form>
    """

@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    print(f"Registered: {username} - {password}")
    return {"message": f"User '{username}' registered successfully!"}