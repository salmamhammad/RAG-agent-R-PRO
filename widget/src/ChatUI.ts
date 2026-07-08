// отрисовка UI
import { sendQuestion, sendFeedback  } from './api';
export class ChatUI {
  private container!: HTMLElement;
  private toggleButton!: HTMLElement;
  private messages: Array<{ role: 'user' | 'assistant', content: string }> = [];
  private input!: HTMLInputElement;
  private chatBox!: HTMLElement;
  private isOpen: boolean = false;
  private hasGreeted: boolean = false;
  constructor() {
      
    this.buildWidget();
    document.body.appendChild(this.container);
    document.body.appendChild(this.toggleButton);

    // Скрываем чат при старте
    this.container.style.display = 'none';

    // Обработчик клика по иконке
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
      width: 350px;
      height: 500px;
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
    // Содержимое чата (заголовок, сообщения, ввод)
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
      font-size: 30px;
      line-height: 60px;
      text-align: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 10000;
      user-select: none;
      transition: background 0.2s;
    `;
    this.setIcon('open');
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
    header.style.cssText = 'background: rgb(203, 0, 0); color: white; padding: 12px; font-weight: bold;';
    header.textContent = 'Чат поддержки';
    const closeBtn = document.createElement('span');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'cursor: pointer; font-size: 18px;';
    closeBtn.addEventListener('click', () => this.toggleChat());
    header.appendChild(closeBtn);
    this.container.appendChild(header);

    // Область сообщений
    this.chatBox = document.createElement('div');
    this.chatBox.style.cssText = 'flex: 1; padding: 12px; overflow-y: auto; background: #f9f9f9;';
    this.container.appendChild(this.chatBox);

    // Поле ввода и кнопка
    const inputRow = document.createElement('div');
    inputRow.style.cssText = 'display: flex; padding: 8px; border-top: 1px solid #ddd; background: white;';
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

    // Кнопка закрытия 
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
          this.setIcon('closed');
          this.toggleButton.title = 'Закрыть чат';
          setTimeout(() => this.input.focus(), 300);

        // Добавляем приветственное сообщение, если ещё не добавляли
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
          this.setIcon('open');
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
      const response = await sendQuestion(text, history);
      this.addMessage('assistant', response.answer);
      // можно отобразить источники
    } catch (err) {
      this.addMessage('assistant', 'Ошибка получения ответа. Попробуйте позже.');
    } finally {
      this.input.disabled = false;
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
    const msg = document.createElement('div');
    msg.style.cssText = `
      margin: 6px 0; padding: 10px; border-radius: 8px;
      max-width: 80%;
      ${role === 'user' ? 'background: #e1f5fe; align-self: flex-end; margin-left: auto;' : 'background: white; align-self: flex-start;'}
    `;
  if (role === 'assistant') {
      const { thought, answer } = this.parseMessage(content);
      // Блок с мыслями (если есть)
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
        `;
        thoughtDiv.textContent = 'печатает: ' + thought;
        thoughtDiv.title = 'Кликните, чтобы скрыть/показать мысли';
  

        msg.appendChild(thoughtDiv);
      }
      // Блок с ответом (основной)
      const answerDiv = document.createElement('div');
      answerDiv.style.cssText = `
        background: white;
        padding: 10px;
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        word-wrap: break-word;
      `;
      answerDiv.textContent = answer;
      msg.appendChild(answerDiv);

    
    } else {
      // Сообщение пользователя
      const userDiv = document.createElement('div');
      userDiv.style.cssText = `
        background: #e1f5fe;
        padding: 10px;
        border-radius: 8px;
        word-wrap: break-word;
      `;
      userDiv.textContent = content;
      msg.appendChild(userDiv);
    }

    this.chatBox.appendChild(msg);
    this.messages.push({ role, content });
    this.chatBox.scrollTop = this.chatBox.scrollHeight;
    }

  private setIcon(state: 'closed' | 'open') {
    if (state === 'closed') {
      // Иконка чата
      this.toggleButton.innerHTML = `
        <svg viewBox="0 0 24 24" fill="white" width="32" height="32">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/>
        </svg>
      `;
    } else {
      // Иконка закрытия
      this.toggleButton.innerHTML = `
        <svg viewBox="0 0 24 24" fill="white" width="32" height="32">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
        </svg>
      `;
    }
  }

}