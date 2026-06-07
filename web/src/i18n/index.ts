import i18n from "i18next";
import { initReactI18next } from "react-i18next";

i18n.use(initReactI18next).init({
  lng: localStorage.getItem("uotp.lng") ?? "ru",
  fallbackLng: "ru",
  interpolation: { escapeValue: false },
  resources: {
    ru: {
      translation: {
        login: "Вход",
        identifier: "Email или телефон",
        password: "Пароль",
        signIn: "Войти",
        signOut: "Выйти",
        language: "Қаз",
        theme: "Тема",
        admin: "Кабинет администратора",
        dispatcher: "Кабинет диспетчера",
        executor: "Кабинет исполнителя",
        akim: "Кабинет акима",
        inspector: "Кабинет инспектора",
        queue: "Очередь задач",
        people: "Пользователи и роли",
        briefing: "Брифинг",
        nextTask: "Следующая задача",
        checks: "Контрольные проверки"
      }
    },
    kk: {
      translation: {
        login: "Кіру",
        identifier: "Email немесе телефон",
        password: "Құпиясөз",
        signIn: "Кіру",
        signOut: "Шығу",
        language: "Рус",
        theme: "Тақырып",
        admin: "Әкімші кабинеті",
        dispatcher: "Диспетчер кабинеті",
        executor: "Орындаушы кабинеті",
        akim: "Әкім кабинеті",
        inspector: "Инспектор кабинеті",
        queue: "Тапсырмалар кезегі",
        people: "Пайдаланушылар мен рөлдер",
        briefing: "Брифинг",
        nextTask: "Келесі тапсырма",
        checks: "Бақылау тексерістері"
      }
    }
  }
});

export default i18n;
