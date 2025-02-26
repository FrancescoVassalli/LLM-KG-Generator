import React, { useState } from "react";
import axios from "axios";

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "User", text: input };
    setMessages([...messages, userMessage]);

    try {
      const response = await axios.post(`http://127.0.0.1:8000/mock/hybrid-answer/${input}`);
      console.log(response)
      const botMessage = { sender: "Bot", text: response.data };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      console.error("Error communicating with API:", error);
    }

    setInput("");
  };

  return (
    <div style={{ maxWidth: "400px", margin: "auto", textAlign: "center" }}>
      <h2>Chatbot</h2>
      <div style={{ height: "300px", overflowY: "auto", border: "1px solid black", padding: "10px" }}>
        {messages.map((msg, index) => (
          <div key={index} style={{ textAlign: msg.sender === "User" ? "right" : "left" }}>
            <strong>{msg.sender}:</strong> {msg.text}
          </div>
        ))}
      </div>
      <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a message..." />
      <button onClick={sendMessage}>Send</button>
    </div>
  );
};

export default Chatbot;
