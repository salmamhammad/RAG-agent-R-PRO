// отрисовка UI
import { sendQuestion, sendFeedback } from './api';
const API_BASE = 'http://localhost:8000'; 
export class ChatUI {
  private container!: HTMLElement;
  private toggleButton!: HTMLElement;
  private messages: Array<{ role: 'user' | 'assistant', content: string }> = [];
  private input!: HTMLInputElement;
  private chatBox!: HTMLElement;
  private isOpen: boolean = false;
  private hasGreeted: boolean = false;
  private ticketId: number | null = null;
  private pollingInterval: any = null;
  private lastEngineerAnswer: string = '';

  constructor() {
    
    this.buildWidget();
    document.body.appendChild(this.container);
    document.body.appendChild(this.toggleButton);

    // Скрываем чат при старте
    this.container.style.display = 'none';
    this.toggleButton.addEventListener('click', () => this.toggleChat());
  }

  private buildWidget() {
    // --- КОНТЕЙНЕР ЧАТА ---
    this.container = document.createElement('div');
    this.container.id = 'rag-chat-widget';
    this.container.style.cssText = `
      position: fixed;
      bottom: 90px;
      right: 20px;
      width: 450px;
      max-height: 80vh;
      height: auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.2);
      display: flex;
      flex-direction: column;
      z-index: 9999;
      overflow: hidden;
      font-family: sans-serif;
      border: 1px solid #ddd;
      transition: opacity 0.3s ease, transform 0.3s ease;
      opacity: 0;
      transform: scale(0.9);
      pointer-events: none;
    `;
    this.buildUI();

    // --- ИКОНКА / КНОПКА-ТРИГГЕР ---
    this.toggleButton = document.createElement('div');
    this.toggleButton.id = 'rag-chat-toggle';
    this.toggleButton.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: rgb(203, 0, 0);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 10000;
      user-select: none;
      transition: background 0.2s;
    `;
    // Начальное состояние — чат закрыт, показываем иконку сообщения
    this.setIcon('closed');
    this.toggleButton.title = 'Открыть чат поддержки';
    this.toggleButton.addEventListener('mouseenter', () => {
      this.toggleButton.style.background = 'rgb(203, 0, 0)';
    });
    this.toggleButton.addEventListener('mouseleave', () => {
      this.toggleButton.style.background = 'rgb(203, 0, 0)';
    });
  }

  private buildUI() {
    // Заголовок
    const header = document.createElement('div');
    header.style.cssText = 'background: rgb(203, 0, 0); color: white; padding: 12px; font-weight: bold; display: flex; justify-content: space-between; align-items: center;';
    header.textContent = 'Чат поддержки';
    const closeBtn = document.createElement('span');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'cursor: pointer; font-size: 18px;';
    closeBtn.addEventListener('click', () => this.toggleChat());
    header.appendChild(closeBtn);
    this.container.appendChild(header);

    // Область сообщений — она будет прокручиваться
    this.chatBox = document.createElement('div');
    this.chatBox.style.cssText = `
      flex: 1 1 auto;
      padding: 12px;
      overflow-y: auto;
      background: #f9f9f9;
      display: flex;
      flex-direction: column;
      min-height: 0;
      max-height: calc(80vh - 100px);
    `;
    this.container.appendChild(this.chatBox);

    // Поле ввода и кнопка отправки
    const inputRow = document.createElement('div');
    inputRow.style.cssText = 'display: flex; padding: 8px; border-top: 1px solid #ddd; background: white; flex-shrink: 0;';
    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.placeholder = 'Задайте вопрос...';
    this.input.style.cssText = 'flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px;';
    const sendBtn = document.createElement('button');
    sendBtn.textContent = 'Отправить';
    sendBtn.style.cssText = 'margin-left: 8px; padding: 8px 16px; background: rgb(203, 0, 0); color: white; border: none; border-radius: 4px; cursor: pointer;';
    sendBtn.onclick = () => this.sendMessage();
    this.input.onkeypress = (e) => { if (e.key === 'Enter') this.sendMessage(); };
    inputRow.appendChild(this.input);
    inputRow.appendChild(sendBtn);
    this.container.appendChild(inputRow);
  }

  private toggleChat() {
    this.isOpen = !this.isOpen;
    const chatContainer = this.container;
    if (this.isOpen) {
      chatContainer.style.display = 'flex';
      requestAnimationFrame(() => {
        chatContainer.style.opacity = '1';
        chatContainer.style.transform = 'scale(1)';
        chatContainer.style.pointerEvents = 'auto';
      });
      // При открытии показываем иконку закрытия
      this.setIcon('open');
      this.toggleButton.title = 'Закрыть чат';
      setTimeout(() => this.input.focus(), 300);

      if (!this.hasGreeted) {
        this.hasGreeted = true;
        this.addMessage('assistant', 'Здравствуйте, я ИИ-помощник R-PRO. Чем я могу вам помочь?');
      }
    } else {
      chatContainer.style.opacity = '0';
      chatContainer.style.transform = 'scale(0.9)';
      chatContainer.style.pointerEvents = 'none';
      setTimeout(() => {
        chatContainer.style.display = 'none';
      }, 300);
      // При закрытии показываем иконку чата
      this.setIcon('closed');
      this.toggleButton.title = 'Открыть чат поддержки';
    }
  }

  private async sendMessage() {
    const text = this.input.value.trim();
    if (!text) return;
    this.addMessage('user', text);
    this.input.value = '';
    this.input.disabled = true;

    try {
      const history = this.messages.map(m => ({ role: m.role, content: m.content }));
      const response = await sendQuestion(text, history, this.ticketId || undefined);
      this.addMessage('assistant', response.answer);
    } catch (err) {
      this.addMessage('assistant', 'Ошибка получения ответа. Попробуйте позже.');
      console.error(err);
    } finally {
      this.input.disabled = false;
      this.input.focus();
    }
  }

  private parseMessage(content: string): { thought: string | null, answer: string } {
    const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
    if (thinkMatch) {
      const thought = thinkMatch[1].trim();
      const answer = content.replace(/<think>[\s\S]*?<\/think>/, '').trim();
      return { thought, answer };
    }
    return { thought: null, answer: content };
  }

  private addMessage(role: 'user' | 'assistant', content: string) {
    // Контейнер для одного сообщения (может содержать и мысли, и ответ)
    const msgContainer = document.createElement('div');
    msgContainer.style.cssText = `
      margin: 6px 0;
      max-width: 100%;
      ${role === 'user' ? 'align-self: flex-end; margin-left: auto;' : 'align-self: flex-start;'}
      width: 100%;
    `;

    if (role === 'assistant') {
      const { thought, answer } = this.parseMessage(content);

      // --- Блок мыслей (если есть) ---
      if (thought) {
        const thoughtDiv = document.createElement('div');
        thoughtDiv.style.cssText = `
          margin-top: 4px;
          padding: 6px 10px;
          background: #f0f0f0;
          border-radius: 4px;
          font-size: 0.85em;
          color: #555;
          font-style: italic;
          cursor: pointer;
          transition: background 0.2s;
          user-select: none;
          word-wrap: break-word;
          white-space: pre-wrap;
          max-width: 100%;
        `;
        if (thought.length > 300) {
          const preview = thought.slice(0, 300) + '... (кликните, чтобы развернуть)';
          thoughtDiv.textContent = 'Посчитать: ' + preview;
          let expanded = false;
          thoughtDiv.addEventListener('click', () => {
            expanded = !expanded;
            thoughtDiv.textContent = expanded ? 'Посчитать: ' + thought : 'Посчитать: ' + preview;
          });
        } else {
          thoughtDiv.textContent = 'Посчитать: ' + thought;
        }
        thoughtDiv.title = 'Кликните, чтобы скрыть/показать мысли';
        msgContainer.appendChild(thoughtDiv);
      }

      // --- Основной ответ (всегда показывается полностью) ---
      const answerDiv = document.createElement('div');
      answerDiv.style.cssText = `
        background: white;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        word-wrap: break-word;
        white-space: pre-wrap;
        overflow-wrap: break-word;
        max-width: 100%;
        margin-top: 4px;
      `;
      answerDiv.textContent = answer;
      msgContainer.appendChild(answerDiv);
      const feedbackContainer = document.createElement('div');
      feedbackContainer.style.cssText = 'display: flex; gap: 8px; margin-top: 6px; align-self: flex-start;';

      // Кнопка "лайк"
      const likeBtn = document.createElement('button');
      likeBtn.style.cssText = 'background: transparent; border: none; cursor: pointer; padding: 0;';
      likeBtn.innerHTML = `
        <div style="width: 32px; height: 32px; border-radius: 50%; background: #f0f0f0; display: flex; align-items: center; justify-content: center; transition: background 0.2s;">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="color: #555;">
            <path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/>
          </svg>
        </div>
      `;
      // Добавляем обработчик и меняем цвет фона после клика
      likeBtn.onclick = () => {
        // Меняем фон кнопки, чтобы показать нажатие
        const circle = likeBtn.querySelector('div');
        if (circle) circle.style.background = '#4caf50';
        this.sendFeedback(content, answer, 1);
      };

      // Кнопка "дизлайк"
      const dislikeBtn = document.createElement('button');
      dislikeBtn.style.cssText = 'background: transparent; border: none; cursor: pointer; padding: 0;';
      dislikeBtn.innerHTML = `
        <div style="width: 32px; height: 32px; border-radius: 50%; background: #f0f0f0; display: flex; align-items: center; justify-content: center; transition: background 0.2s;">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" style="color: #555;">
            <path d="M15 3H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2c0 1.1.9 2 2 2h6.31l-.95 4.57-.03.32c0 .41.17.79.44 1.06L9.83 23l6.59-6.59c.36-.36.58-.86.58-1.41V5c0-1.1-.9-2-2-2zm4 0v12h4V3h-4z"/>
          </svg>
        </div>
      `;
      dislikeBtn.onclick = () => {
        const circle = dislikeBtn.querySelector('div');
        const dislikesNum=localStorage.getItem('dislikesNum');
        if(dislikesNum){
           localStorage.setItem('dislikesNum', dislikesNum+1);
        }else{
           localStorage.setItem('dislikesNum', '0');
        }
        if (circle) circle.style.background = '#f44336'; 
        this.sendFeedback(content, answer, -1);
      };

      feedbackContainer.appendChild(likeBtn);
      feedbackContainer.appendChild(dislikeBtn);
      msgContainer.appendChild(feedbackContainer);

    } else {
      // Сообщение пользователя
      const userDiv = document.createElement('div');
      userDiv.style.cssText = `
        background: #e1f5fe;
        padding: 10px;
        border-radius: 8px;
        word-wrap: break-word;
        max-width: 100%;
        white-space: pre-wrap;
        overflow-wrap: break-word;
        align-self: flex-end;
      `;
      userDiv.textContent = content;
      msgContainer.appendChild(userDiv);
    }

    this.chatBox.appendChild(msgContainer);
    this.messages.push({ role, content });
    // Прокрутка вниз после добавления
    this.chatBox.scrollTop = this.chatBox.scrollHeight;
  }

  /**
   * Устанавливает иконку на кнопку-триггер
   * @param state 'closed' — чат закрыт (показываем иконку сообщения)
   *               'open'   — чат открыт (показываем иконку закрытия)
   */
  private setIcon(state: 'closed' | 'open') {
    if (state === 'closed') {
      // Иконка чата (облачко с тремя точками)
      this.toggleButton.innerHTML = `
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="9" cy="10" r="1.5" fill="white"/>
          <circle cx="12" cy="10" r="1.5" fill="white"/>
          <circle cx="15" cy="10" r="1.5" fill="white"/>
        </svg>
      `;
    } else {
      // Иконка закрытия (крестик)
      this.toggleButton.innerHTML = `
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M18 6L6 18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M6 6L18 18" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      `;
    }
  }
  private async sendFeedback(question: string, answer: string, rating: number) {
    try {
        // const ticketId= localStorage.getItem('ticket_id');
        const history = this.messages.map(m => ({ role: m.role, content: m.content }));
        const response = await sendFeedback(question, answer, rating, history,undefined, this.ticketId );
        console.log('[ChatUI] Ответ фидбэка:', response);
        const dislikesNum=localStorage.getItem('dislikesNum');
        if (dislikesNum) {
            const count = parseInt(dislikesNum, 0);
            if (count >= 3) {
               // Можно сохранить ticket_id в localStorage для опроса
               this.ticketId = response.ticket_id;
               localStorage.setItem('ticket_id', String(response.ticket_id));
               this.addMessage('assistant', ` Инженер вызван. Номер заявки #${response.ticket_id}. Ожидайте ответа.`);
               this.startPollingTicket(response.ticket_id);
               
        } else {
            // Если ticket_id нет, значит дизлайк учтён, но инженер не вызван
            console.log('Дизлайк учтён, тикет не создан (меньше 3 дизлайков или уже есть тикет)');
        }
      }else {
            // Если ticket_id нет, значит дизлайк учтён, но инженер не вызван
            console.log('Дизлайк учтён, тикет не создан (меньше 3 дизлайков или уже есть тикет)');
        }
    } catch (err) {
        console.error('Ошибка отправки фидбэка:', err);
    }
  }

    private startPollingTicket(ticketId: number) {
    // Останавливаем предыдущий опрос, если был
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
    console.log(`[ChatUI] Начинаем опрос тикета #${ticketId}`);
    this.pollingInterval = setInterval(async () => {
      try {
        const url = `${API_BASE}/ticket/${ticketId}`;
        const resp = await fetch(url);
        if (!resp.ok) {
          if (resp.status === 404) {
            console.warn(`[ChatUI] Тикет #${ticketId} не найден, останавливаем опрос.`);
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
            localStorage.removeItem('ticket_id');
            this.ticketId = null;
            return;
          }
          throw new Error(`HTTP ${resp.status}`);
        }
        const data = await resp.json();
        console.log(`[ChatUI] Статус тикета #${ticketId}:`, data);

        // Если тикет закрыт
        if (data.status === 'closed') {
          clearInterval(this.pollingInterval);
          this.pollingInterval = null;
          localStorage.removeItem('ticket_id');
          this.ticketId = null;
          if (data.answer && data.answer !== this.lastEngineerAnswer) {
            this.addMessage('assistant', `🛠️ Инженер ответил:\n${data.answer}`);
            localStorage.setItem('dislikesNum', '0');
            this.lastEngineerAnswer = data.answer;
          }
          this.addMessage('assistant', '✅ Тикет закрыт. Если у вас остались вопросы, задайте их в новом диалоге.');
          return;
        }

        // Если появился новый ответ от инженера
        if (data.answer && data.answer !== this.lastEngineerAnswer) {
          this.lastEngineerAnswer = data.answer;
          this.addMessage('assistant', `🛠️ Инженер ответил:\n${data.answer}`);
          // Прокручиваем вниз
          this.chatBox.scrollTop = this.chatBox.scrollHeight;
        }

        // Если статус изменился на in_progress и ранее не было ответа
        if (data.status === 'in_progress' && data.answer && data.answer !== this.lastEngineerAnswer) {
          // уже обработано выше
        }
      } catch (e) {
        console.error('[ChatUI] Ошибка опроса тикета:', e);
      }
    }, 5000); // каждые 5 секунд
  }
}