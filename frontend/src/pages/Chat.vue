<template>
  <div class="chat-container">
    <div class="chat-welcome">
      <div class="welcome-icon">🔥</div>
      <h2>欢迎使用 HeatAI 供热智能客服</h2>
      <p>我是您的供热服务助手，可以帮您解答供暖相关问题</p>
      <div class="quick-questions">
        <h4>您可以尝试问我：</h4>
        <el-tag
          v-for="q in quickQuestions"
          :key="q"
          class="quick-tag"
          @click="handleQuickQuestion(q)"
        >
          {{ q }}
        </el-tag>
      </div>
    </div>
    <div class="chat-input-area">
      <el-input
        v-model="inputMessage"
        type="textarea"
        :rows="3"
        placeholder="请输入您的问题..."
        resize="none"
        @keydown.enter.exact="handleSend"
      />
      <el-button
        type="primary"
        :disabled="!inputMessage.trim()"
        class="send-btn"
        @click="handleSend"
      >
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const inputMessage = ref('')

const quickQuestions = [
  '暖气不热怎么办？',
  '供暖温度标准是多少？',
  '如何缴纳供暖费？',
  '报修流程是怎样的？'
]

function handleQuickQuestion(question: string) {
  inputMessage.value = question
}

function handleSend() {
  if (!inputMessage.value.trim()) return
  ElMessage.info('聊天功能将在后续版本中实现')
  inputMessage.value = ''
}
</script>

<style scoped>
.chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.chat-welcome h2 {
  font-size: 24px;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.chat-welcome p {
  font-size: 15px;
  color: #909399;
  margin-bottom: 30px;
}

.quick-questions {
  text-align: center;
}

.quick-questions h4 {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
  font-weight: 500;
}

.quick-tag {
  margin: 4px 6px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 16px;
  padding: 6px 16px;
  font-size: 13px;
}

.quick-tag:hover {
  background-color: #ff6b35;
  color: #fff;
  border-color: #ff6b35;
}

.chat-input-area {
  display: flex;
  gap: 12px;
  padding: 20px 24px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  align-items: flex-end;
}

.send-btn {
  height: 40px;
  background: linear-gradient(135deg, #ff6b35, #f7931e);
  border: none;
  border-radius: 8px;
  padding: 0 24px;
  font-size: 14px;
}

.send-btn:hover {
  background: linear-gradient(135deg, #e55d2b, #e6840e);
}
</style>
