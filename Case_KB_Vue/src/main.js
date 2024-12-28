import { createApp } from 'vue'
import Base from './Base.vue'
import router from './router'
import store from './store'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap'
import '@fortawesome/fontawesome-free/css/all.min.css'

const app = createApp(Base)
app.use(router)
app.use(store)
app.mount('#app') 