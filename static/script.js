const apiBaseUrl = "http://127.0.0.1:8000";
let access_token;
// Асинхронная функция для получения списка пользователей и обновления HTML - списка;
document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  let username = document.getElementById("login").value;
  let password = document.getElementById("password").value;
  const formData = new FormData();
  formData.append("grant_type", "password"); // добавляем grant_type
  formData.append("username", username); // добавляем имя пользователя
  formData.append("password", password); // добавляем пароль
  const response = await fetch(`${apiBaseUrl}/token`, {
    method: "POST",
    body: formData,
  });
  const token = await response.json();
  access_token = token.access_token;
  fetchUsers();
});

async function fetchUsers() {
  // Выполняем GET-запрос к API для получения списка пользователей
  const response = await fetch(`${apiBaseUrl}/users/`, {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${access_token}`,
    },
  });
  // Преобразуем ответ в JSON-формат
  const users = await response.json();
  // Получаем элемент списка пользователей по его ID
  const userList = document.getElementById("user-list");
  // Очищаем текущий список пользователей
  userList.innerHTML = "";
  // Проходим по каждому пользователю и добавляем его в HTML-список
  users.forEach((user) => {
    const li = document.createElement("li");
    li.textContent = `${user.id}: ${user.username} (${user.email})`;
    userList.appendChild(li);
  });
}
// Обработчик события отправки формы создания пользователя
document
  .getElementById("create-user-form")
  .addEventListener("submit", async (e) => {
    // Предотвращаем стандартное поведение формы (перезагрузку страницы)
    e.preventDefault();
    // Получаем значения полей формы
    const username = document.getElementById("username").value;
    const email = document.getElementById("email").value;
    const full_name = document.getElementById("full_name").value;
    const password = document.getElementById("password").value;

    // Отправляем POST-запрос на сервер для создания нового пользователя
    const response = await fetch(`${apiBaseUrl}/register/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, full_name, password }),
    });

    // Проверяем успешность операции и показываем сообщение пользователю
    if (response.ok) {
      alert("User created successfully");
      // Обновляем список пользователей
      fetchUsers();
    } else {
      alert("Error creating user");
    }
  });

// Обработчик события отправки формы обновления пользователя
document
  .getElementById("update-user-form")
  .addEventListener("submit", async (e) => {
    // Предотвращаем стандартное поведение формы
    e.preventDefault();
    // Получаем значения полей формы
    const userId = document.getElementById("update-user-id").value;

    const username = document.getElementById("update-username").value;
    const email = document.getElementById("update-email").value;
    const full_name = document.getElementById("update-full_name").value;
    const password = document.getElementById("update-password").value;

    // Отправляем PUT-запрос на сервер для обновления данных пользователя
    const response = await fetch(`${apiBaseUrl}/users/${userId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${access_token}`,
      },
      body: JSON.stringify({ username, email, full_name, password }),
    });

    // Проверяем успешность операции и показываем сообщение пользователю
    if (response.ok) {
      alert("User updated successfully");
      // Обновляем список пользователей
      fetchUsers();
    } else {
      alert("Error updating user");
    }
  });

document
  .getElementById("users-me-form")
  .addEventListener("submit", async (e) => {
    e.preventDefault();
    const response = await fetch(`${apiBaseUrl}/users/me`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${access_token}`,
      },
    });

    // Проверяем успешность операции и показываем сообщение пользователю
    if (response.ok) {
      alert("User successfully get info");
      const info = await response.json();
      console.log(info);
      const userInfoDiv = document.getElementById("user-info");

      // Создаем и добавляем элементы для отображения данных пользователя
      for (const [key, value] of Object.entries(info)) {
        const p = document.createElement("p");
        p.textContent = `${key}: ${value}`;
        userInfoDiv.appendChild(p);
      }

      // Обновляем список пользователей
      fetchUsers();
    } else {
      alert("Error getting info for user");
    }
  });

// Обработчик события отправки формы удаления пользователя
document
  .getElementById("delete-user-form")
  .addEventListener("submit", async (e) => {
    // Предотвращаем стандартное поведение формы
    e.preventDefault();
    // Получаем ID пользователя для удаления
    const userId = document.getElementById("delete-user-id").value;

    // Отправляем DELETE-запрос на сервер для удаления пользователя
    const response = await fetch(`${apiBaseUrl}/users/${userId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${access_token}`,
      },
    });

    // Проверяем успешность операции и показываем сообщение пользователю
    if (response.ok) {
      alert("User deleted successfully");
      // Обновляем список пользователей
      fetchUsers();
    } else {
      alert("Error deleting user");
    }
  });

// При загрузке страницы выполняем начальное получение списка пользователей
