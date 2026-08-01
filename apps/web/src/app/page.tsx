/**
 * 首页 - 重定向到登录
 */
import { redirect } from "next/navigation";

export default function HomePage() {
  redirect("/login");
}
