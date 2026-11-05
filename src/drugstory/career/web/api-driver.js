/* One transport for text and scene. Never predicts or mutates game state locally. */
(function (root) {
  class ApiDriver {
    constructor(
      fetcher = (...args) => fetch(...args),
      uuid = () => crypto.randomUUID(),
    ) {
      this.fetcher = fetcher;
      this.uuid = uuid;
      this.current = null;
      this.content = null;
      this.busy = false;
      this.uncertain = false;
    }
    async read(path) {
      const response = await this.fetcher(path);
      if (!response.ok)
        throw new Error(`连接失败（${response.status}），请重新连接。`);
      return response.json();
    }
    async connect() {
      this.content = await this.read("/api/content");
      if (this.content.api_version !== 2)
        throw new Error("引擎接口版本不兼容，请使用配套版本。");
      const current = await this.read("/api/state");
      this.current = current;
      this.uncertain = false;
      return current;
    }
    async act(name, args = {}) {
      if (this.busy) throw new Error("上一项操作仍在保存，请稍候。");
      if (this.uncertain)
        throw new Error("上次操作的保存结果尚未确认，请先重新连接。");
      this.busy = true;
      const body = JSON.stringify({
        name,
        args,
        revision: this.current.revision,
        request_id: this.uuid(),
      });
      const options = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Game-Token": this.current.token,
        },
        body,
      };
      try {
        let response;
        // Retry a lost response with the SAME identity; the server deduplicates it.
        for (let attempt = 0; attempt < 2; attempt++) {
          try {
            response = await this.fetcher("/api/action", options);
            break;
          } catch (error) {
            if (attempt) {
              this.uncertain = true;
              throw new Error(
                "连接中断，操作可能已保存。请重新连接确认进度。",
                { cause: error },
              );
            }
          }
        }
        let data;
        try {
          data = await response.json();
        } catch (error) {
          this.uncertain = true;
          throw new Error("返回内容不完整，请重新连接确认进度。", {
            cause: error,
          });
        }
        if (!response.ok) {
          if (data.state) this.current = data.state;
          if (response.status === 403) this.uncertain = true;
          throw new Error(data.error || `操作失败（${response.status}）`);
        }
        this.current = data;
        return data;
      } finally {
        this.busy = false;
      }
    }
    tick() {
      return this.act("advance", { weeks: 1 });
    }
    view() {
      return this.current;
    }
  }
  root.DrugstoryApiDriver = ApiDriver;
  if (typeof module !== "undefined") module.exports = ApiDriver;
})(typeof window === "undefined" ? globalThis : window);
