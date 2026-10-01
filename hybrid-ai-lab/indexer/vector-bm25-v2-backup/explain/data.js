window.EXPLAIN_DATA = {
  meta: {
    title: "우리 코드로 이해하는 벡터DB 만들기",
    entry: "run_indexer.py",
    lang: "python"
  },
  files: [
    {
      id: "entry",
      label: "run_indexer.py",
      role: "명령행 인덱서를 시작하는 가장 바깥쪽 진입 파일",
      lang: "python"
    },
    {
      id: "cli",
      label: "app/presentation/cli.py",
      role: "사용자가 준 옵션을 인덱싱 요청으로 바꾸고 결과를 출력하는 파일",
      lang: "python"
    },
    {
      id: "bootstrap",
      label: "app/bootstrap.py",
      role: "로더·분할기·정제기·임베더·저장소를 한 서비스로 연결하는 파일",
      lang: "python"
    },
    {
      id: "models",
      label: "app/domain/models.py",
      role: "800토큰과 최대 200토큰 중첩이라는 청킹 규칙을 정의하는 파일",
      lang: "python"
    },
    {
      id: "loaders",
      label: "app/infrastructure/loaders.py",
      role: "PDF와 상담 텍스트를 원문 좌표가 있는 메모리 문서로 읽는 파일",
      lang: "python"
    },
    {
      id: "splitter",
      label: "app/infrastructure/splitter.py",
      role: "문서를 의미 있는 경계부터 시도해 토큰 상한 안의 조각으로 나누는 파일",
      lang: "python"
    },
    {
      id: "text_rules",
      label: "app/domain/text_rules.py",
      role: "제외 구간과 개인정보 치환 규칙을 원문 좌표에 적용하는 파일",
      lang: "python"
    },
    {
      id: "processor",
      label: "app/infrastructure/processor.py",
      role: "정제 결과를 검사하고 저장 가능한 청크와 메타데이터를 만드는 파일",
      lang: "python"
    },
    {
      id: "workflow",
      label: "app/application/indexing_service.py",
      role: "로드부터 적재까지 순서를 조정하고 재사용·재개 상태를 관리하는 파일",
      lang: "python"
    },
    {
      id: "embedder",
      label: "app/infrastructure/embedder.py",
      role: "정제된 청크를 의미를 나타내는 고정 길이 숫자 벡터로 바꾸는 파일",
      lang: "python"
    },
    {
      id: "repository",
      label: "app/infrastructure/index_repository.py",
      role: "청크·벡터·메타데이터를 새 Chroma 세대에 안전하게 적재하는 파일",
      lang: "python"
    }
  ],
  flow: [
    {
      step: 1,
      title: "실행 준비",
      label: "준비",
      summary: "명령행 옵션을 읽고 다섯 단계의 담당 객체를 한 서비스로 연결합니다.",
      detail: "run_indexer.py가 cli.main()을 부르고, bootstrap.create_service()가 로더·분할기·정제기·임베더·저장소를 연결합니다. 이때 아직 모델 추론이나 문서 처리는 시작하지 않습니다.",
      refs: ["entrypoint", "cli_main", "create_service"]
    },
    {
      step: 2,
      title: "로드",
      label: "1. 로드",
      summary: "파일을 찾고, PDF 또는 상담 텍스트를 원문 좌표가 있는 메모리 문서로 읽습니다.",
      detail: "실제 예로 docs/D3_S01_신규가입_상담이력_합성.txt는 D3 정책에 맞아 상담 레코드별 문서가 됩니다. 개인정보 원문을 그대로 저장하지 않고, 나중에 치환할 문자 위치를 함께 표시합니다.",
      refs: ["discover", "load"]
    },
    {
      step: 3,
      title: "청킹",
      label: "2. 청킹",
      summary: "긴 문서를 검색과 임베딩이 다루기 좋은 크기의 청크로 나눕니다.",
      detail: "800은 800글자가 아니라 임베딩 모델이 읽는 토큰 수의 상한입니다. 200도 고정 중첩량이 아니라 최대 중첩 토큰 수입니다. 조항·문장·줄 경계를 먼저 찾으므로 실제 중첩은 200보다 작을 수 있습니다.",
      refs: ["split_policy", "split"]
    },
    {
      step: 4,
      title: "정제",
      label: "3. 정제",
      summary: "청크에서 반복 여백을 제거하고 정해진 개인정보 규칙을 적용한 뒤 저장 계약을 검사합니다.",
      detail: "본문의 전화번호·이메일·회원번호 등은 [삭제]로 바꾸고, 생년월일과 나이는 연령대로 일반화합니다. 회원·상담사 원문 식별자는 본문 정제와 별도로 로더가 가명 ID로 만들어 메타데이터에 둡니다. 그 다음 잔존 개인정보·토큰 수·필수 메타데이터를 검사합니다. 실제 순서는 로드 다음에 청킹하고, 각 청크를 정제하는 방식입니다.",
      refs: ["load_split_clean", "clean_chunk_text", "process"]
    },
    {
      step: 5,
      title: "임베딩",
      label: "4. 임베딩",
      summary: "정제된 글을 의미가 가까운 정도를 계산할 수 있는 숫자 벡터로 바꿉니다.",
      detail: "HuggingFaceEmbedder는 입력 순서를 유지하며 모델 출력을 L2 노름 1로 맞춥니다. 워크플로우는 청크를 배치로 보내고 중간 벡터를 산출물로 저장하여 중단 후 다시 시작할 수 있게 합니다.",
      refs: ["workflow_embed", "embed_texts"]
    },
    {
      step: 6,
      title: "적재와 확인",
      label: "5. 적재",
      summary: "청크 본문·벡터·메타데이터를 비활성 Chroma 세대에 넣은 뒤 검증된 세대만 게시합니다.",
      detail: "저장소는 청크 ID, 본문, 벡터, 메타데이터를 한 묶음으로 upsert합니다. 보관된 감사 결과에서는 8개 원천이 192개 청크가 되었고, 토큰 수는 305~748, 벡터 차원은 768, 잔존 개인정보 형식 일치는 0건이었습니다. 이는 이미 저장된 실행 기록이며 이번 설명 페이지 작성 중 인덱서를 다시 실행한 결과는 아닙니다.",
      refs: ["workflow_upsert", "repository_begin", "repository_upsert"]
    }
  ],
  functions: [
    {
      id: "entrypoint",
      name: "run_indexer.py 진입 코드",
      fileId: "entry",
      summary: "운영체제가 받은 실행을 cli.main()으로 넘기고 종료 코드를 돌려줍니다.",
      how: "현관에서 담당 안내원에게 방문 목적을 넘기는 역할입니다. 실제 문서 처리는 이 파일이 직접 하지 않습니다.",
      terms: ["진입점", "종료 코드", "__name__"],
      lines: [
        { at: "from app.presentation.cli import main", text: "실제 명령행 처리를 맡은 main 함수를 가져옵니다." },
        { at: "if __name__ == \"__main__\":", text: "이 파일을 직접 실행했을 때만 아래 코드를 실행합니다." },
        { at: "raise SystemExit(main())", text: "main의 숫자 결과를 운영체제가 읽는 종료 코드로 전달합니다." }
      ],
      code: `\"\"\"명령행 인덱서를 실행하고 응용 결과의 종료 코드를 운영체제에 전달함.\"\"\"

from app.presentation.cli import main

if __name__ == \"__main__\":
    raise SystemExit(main())`
    },
    {
      id: "cli_main",
      name: "main()",
      fileId: "cli",
      summary: "사용자 옵션을 IndexRequest로 묶어 서비스를 실행하고 JSON 결과를 출력합니다.",
      how: "접수 창구가 신청서의 항목을 확인해 내부 처리팀에 넘기는 과정입니다. 오류가 나면 자동화 도구가 알아볼 수 있도록 JSON과 종료 코드를 남깁니다.",
      terms: ["CLI", "IndexRequest", "thread_id", "지연 import", "종료 코드"],
      lines: [
        { at: "parser = argparse.ArgumentParser", text: "명령행에서 받을 옵션의 설명서를 만듭니다." },
        { at: "thread_id = args.thread_id or", text: "재개에 사용할 실행 ID가 없으면 새 ID를 만듭니다." },
        { at: "from app.bootstrap import create_cli_service", text: "도움말만 볼 때 무거운 모듈을 읽지 않도록 서비스 조립을 늦게 가져옵니다." },
        { at: "result = service.run(request)", text: "준비한 요청으로 전체 인덱싱 흐름을 실행합니다." },
        { at: "return result.exit_code", text: "성공 또는 처리 결과의 종료 코드를 호출자에게 돌려줍니다." }
      ],
      code: `def main(argv: list[str] | None = None) -> int:
    \"\"\"명령행 인덱싱 요청을 실행하고 자동화 도구가 판단할 종료 코드를 반환함.

    인자: argv가 None이면 프로세스의 명령행 인자를 사용함.
    반환값: 정상 실행은 서비스의 종료 코드, 사용자 중단은 130, 실행 중 오류는 1임.
    예외: 옵션 해석은 argparse에 맡기므로 도움말·잘못된 옵션은 SystemExit로 처리됨.
    부수효과: 서비스가 인덱스를 갱신할 수 있으며 결과 JSON은 표준 출력, 실행 ID·오류는 표준 오류에 기록함.
    \"\"\"
    parser = argparse.ArgumentParser(description=\"문서별 구분자와 800/200토큰으로 Chroma·BM25를 구축합니다.\")
    parser.add_argument(\"--input\", help=\"원문 디렉터리 또는 파일\")
    parser.add_argument(\"--output\", help=\"결과 디렉터리\")
    parser.add_argument(\"--doc\", choices=(\"all\", \"D1\", \"D2\", \"D3\"), default=\"all\")
    parser.add_argument(\"--segment\", type=int, help=\"D3 상담 세그먼트 번호(1~6)\")
    parser.add_argument(\"--thread-id\", help=\"중단된 실행과 같은 값을 주면 체크포인트부터 재개합니다.\")
    parser.add_argument(\"--full-reindex\", action=\"store_true\")
    parser.add_argument(\"--dry-run\", action=\"store_true\", help=\"정제·청킹·검증까지 수행하고 색인은 게시하지 않습니다.\")
    args = parser.parse_args(argv)
    thread_id = args.thread_id or datetime.now(timezone.utc).strftime(\"%Y%m%dT%H%M%SZ-\") + uuid4().hex[:8]
    # 처리 시작 전에 실행 ID를 남겨 중단되어도 같은 ID로 재개할 수 있게 함.
    print(f\"thread_id={thread_id}\", file=sys.stderr, flush=True)
    try:
        # 도움말만 조회할 때는 모델·저장소 조립에 필요한 모듈을 불필요하게 읽지 않음.
        from app.bootstrap import create_cli_service
        service, input_path, output_path = create_cli_service({\"INPUT_PATH\": args.input, \"OUTPUT_PATH\": args.output})
        request = IndexRequest(input_path=input_path, output_path=output_path, doc=args.doc,
                               segment=args.segment, thread_id=thread_id, full_reindex=args.full_reindex,
                               dry_run=args.dry_run)
        result = service.run(request)
        print(result.model_dump_json(indent=2))
        return result.exit_code
    except KeyboardInterrupt:
        # 명령행 중단 관례인 130을 사용하여 일반 실행 오류와 구분함.
        print(json.dumps({\"status\": \"interrupted\", \"thread_id\": thread_id}, ensure_ascii=False), file=sys.stderr)
        return 130
    except Exception as error:
        # 호출자가 실패를 자동 판정할 수 있게 오류 종류·메시지를 JSON과 종료 코드 1로 전달함.
        print(json.dumps({\"status\": \"error\", \"thread_id\": thread_id,
                          \"error_type\": type(error).__name__, \"message\": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1`
    },
    {
      id: "create_service",
      name: "create_service()",
      fileId: "bootstrap",
      summary: "다섯 단계의 실제 구현체를 만들고 IndexingWorkflow에 연결합니다.",
      how: "조립 설명서를 보고 작업대에 로더·분할기·정제기·임베더·저장소를 순서대로 놓는 과정입니다. 각 객체는 맡은 일만 하고, 워크플로우가 이들을 호출합니다.",
      terms: ["의존성 주입", "포트", "토크나이저", "Chroma", "BM25", "LangGraph"],
      lines: [
        { at: "counter = ports.get(\"token_counter\")", text: "청킹과 임베딩이 같은 토큰 기준을 쓰도록 계산기를 하나 준비합니다." },
        { at: "embedder = ports.get(\"embedder\")", text: "글을 숫자 벡터로 바꿀 임베더를 준비합니다." },
        { at: "repository = ports.get(\"repository\")", text: "벡터와 BM25 결과를 보관할 저장소를 준비합니다." },
        { at: "workflow = IndexingWorkflow(", text: "각 담당 객체를 실제 처리 순서를 아는 워크플로우에 연결합니다." },
        { at: "upsert_batch_size=64", text: "적재는 최대 64개씩 나눠 중단 후 재개할 범위를 작게 유지합니다." }
      ],
      code: `def create_service(settings: Settings | None = None, **ports: Any) -> IndexingService:
    \"\"\"인덱싱 서비스를 구성하되 시험에서는 포트 구현체를 교체할 수 있게 함.

    방법: 전달된 포트를 우선 사용하고 나머지는 파일·모델·Chroma·BM25·LangGraph 구현체로 구성함.
    인자: settings가 없으면 설정 파일과 환경변수를 읽음. ports는 시험에서 대체할 계약 이름별 구현체임.
    반환값: 실행 준비가 된 서비스임. 실제 원천 처리와 임베딩은 서비스를 실행할 때 수행함.
    예외: 잘못된 설정은 ValueError 등으로 전달되며 경로 접근 실패는 OSError 계열 예외로 전달됨.
    부수효과: 기본 저장소 구현체 생성 시 결과·산출물 디렉터리를 만들 수 있음.
    \"\"\"
    config = settings or load_settings()
    
    # 임베딩 모델의 토크나이저(문장을 토큰으로 자르고 각 조각을 번호로 바꿈. 모델이 이 번호별 조각을 임베딩함)
    # 분할과 임베딩이 같은 모델 revision을 사용해야 토큰 상한의 기준이 어긋나지 않음.
    counter = ports.get(\"token_counter\") or ModelTokenCounter(
        config.model_name, config.model_revision, config.max_tokens, local_files_only=config.local_files_only)
    
    # 임베딩 처리 객체 
    embedder = ports.get(\"embedder\") or HuggingFaceEmbedder(
        config.model_name, revision=config.model_revision, max_seq_length=config.max_tokens,
        batch_size=config.batch_size, device=config.device, local_files_only=config.local_files_only,
        expected_dimension=config.embedding_dimension)
    
    # 벡터와 BM25 인덱스 저장 처리 객체   
    repository = ports.get(\"repository\") or GenerationIndexRepository(
        config.output_path, collection=config.collection, lexical_builder=LexicalIndexBuilder(),
        lock_path=config.output_path / \".publish.lock\")
    
    # 워크플로우 처리 객체  
    workflow = IndexingWorkflow(
        sources=ports.get(\"sources\") or FileSystemSourceCatalog(config.policies),
        loader=ports.get(\"loader\") or ConfiguredDocumentLoader(config.policies, config.profiles),
        splitter=ports.get(\"splitter\") or RecursiveDocumentSplitter(counter, config.policies),
        token_counter=counter, 
        processor=ports.get(\"processor\") or ValidatingChunkProcessor(counter, config.metadata_schema),
        embedder=embedder, repository=repository,
        artifacts=ports.get(\"artifacts\") or JsonArtifactStore(config.output_path / \"artifacts\"),
        policies=config.split_policies, default_policy=SplitPolicy(),
        policy_signature=config.policy_signature, 
        profile_signature=config.profile_signature,
        embedding_contract=config.embedding_contract,
        embed_batch_size=config.batch_size, 
        upsert_batch_size=64,  # 적재는 최대 64개씩 저장해 재개 단위를 제한함
    )
    
    # 실행 전체 잠금과 게시 잠금을 분리함. 그래프의 게시 노드는 호출자와 다른 스레드에서 실행될 수 있음.
    runner = ports.get(\"runner\") or LockedPipelineRunner(
        LangGraphPipeline(workflow, config.output_path / \"checkpoints\" / \"indexing.sqlite\",
                          progress=ports.get(\"progress\") or ConsoleProgressReporter()),
        config.output_path / \".writer.lock\",
    )
    
    # 무변경 실행에서 모델을 불필요하게 읽지 않도록 설정 차원을 전달하고 실제 로딩 시 별도로 검증함.
    return IndexingService(runner, policy_signature=config.policy_signature,
                           profile_signature=config.profile_signature, embedding_signature=embedder.signature,
                           embedding_dimension=config.embedding_dimension)`
    },
    {
      id: "split_policy",
      name: "SplitPolicy",
      fileId: "models",
      summary: "청크의 최대 크기와 중첩 상한, 경계를 찾는 순서를 한곳에 보관합니다.",
      how: "800쪽짜리 책이라는 뜻이 아니라 모델이 세는 작은 읽기 단위가 최대 800개라는 뜻입니다. 200은 앞 청크와 반드시 겹치는 양이 아니라 최대 허용량입니다.",
      terms: ["토큰", "특수 토큰", "청크", "중첩", "구분자", "데이터클래스"],
      lines: [
        { at: "chunk_size: int = 800", text: "특수 토큰을 포함해 청크 하나가 가질 수 있는 최대 토큰 수입니다." },
        { at: "chunk_overlap: int = 200", text: "다음 청크가 되짚을 수 있는 최대 토큰 수입니다. 실제 값은 경계에 따라 더 작을 수 있습니다." },
        { at: "separators: tuple[str, ...]", text: "빈 줄, 줄, 공백, 마지막 문자 순으로 나눌 경계를 시도합니다." },
        { at: "if self.chunk_size <= 0", text: "크기와 중첩이 앞으로 진행할 수 있는 값인지 즉시 검사합니다." }
      ],
      code: `@dataclass(frozen=True)
class SplitPolicy:
    \"\"\"문서 유형별로 공통 분할기에 적용할 경계와 길이 조건을 보관함.

    조립 지점이 설정에서 만든 값을 받으며, 토큰 계산이나 실제 분할은 수행하지 않음.
    \"\"\"

    chunk_size: int = 800  # 사용자 확정 청크 상한(임베딩 특수토큰을 포함한 토큰 수)
    chunk_overlap: int = 200  # 사용자 확정 중첩 상한으로 실제 중첩은 분할 경계에 따라 달라짐
    separators: tuple[str, ...] = (r\"\\n\\n\", r\"\\n\", \" \", \"\")  # 먼저 시도할 정규식 경계부터 나열함

    def __post_init__(self) -> None:
        \"\"\"분할이 앞으로 진행할 수 없는 크기·중첩·최후 구분자 조합을 ValueError로 거부함.\"\"\"
        if self.chunk_size <= 0 or not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError(\"청크 크기는 양수이고 중첩은 크기보다 작아야 합니다.\")
        if not self.separators or self.separators[-1] != \"\":
            raise ValueError(\"구분자의 마지막에는 긴 문자열을 나눌 빈 문자열이 필요합니다.\")`
    },
    {
      id: "discover",
      name: "FileSystemSourceCatalog.discover()",
      fileId: "loaders",
      summary: "입력 폴더에서 정책에 맞는 파일을 찾고 내용 지문을 붙입니다.",
      how: "택배를 열기 전에 송장 목록과 봉인 지문을 만드는 단계입니다. 같은 이름이어도 내용이 바뀌면 SHA-256이 달라져 변경을 알아챕니다.",
      terms: ["SHA-256", "SourceRef", "심볼릭 링크", "문서 정책"],
      lines: [
        { at: "candidates = [root] if root.is_file()", text: "입력이 파일이면 그 하나를, 폴더이면 바로 아래 후보를 모읍니다." },
        { at: "if not path.is_file() or path.is_symlink()", text: "일반 파일이 아니거나 다른 위치를 가리키는 링크이면 건너뜁니다." },
        { at: "doc_key = self._doc_key(path.name)", text: "파일명 정책으로 D1·D2·D3 중 어떤 문서인지 정합니다." },
        { at: "digest = sha256(path.read_bytes()).hexdigest()", text: "파일 전체 바이트로 변경 감지용 지문을 만듭니다." }
      ],
      code: `    def discover(self, input_path: str, doc: str, segment: int | None) -> list[SourceRef]:
        \"\"\"입력 경로에서 선택 조건에 맞는 원천과 SHA-256 지문을 찾음.

        인자: doc은 all 또는 문서 키이며, segment는 D3 파일명의 S번호 필터임.
        반환값: 경로·파일명·문서 키·원본 파일 해시를 담은 목록임.
        예외: 입력 경로를 읽을 수 없으면 pathlib 파일 예외가 전파됨.
        부수효과: 후보 파일 전체를 읽어 내용 해시를 계산함.
        \"\"\"

        root = Path(input_path)
        candidates = [root] if root.is_file() else sorted(root.glob(\"*\"))
        result: list[SourceRef] = []
        for path in candidates:
            if not path.is_file() or path.is_symlink() or \"_instructor\" in path.name.lower():
                continue
            doc_key = self._doc_key(path.name)
            if not doc_key or (doc.lower() != \"all\" and doc_key.lower() != doc.lower()):
                continue
            if segment is not None and doc_key == \"D3\" and f\"_S{segment:02d}_\" not in path.name:
                continue
            digest = sha256(path.read_bytes()).hexdigest()
            result.append(SourceRef(str(path.resolve()), path.name, doc_key, digest))
        return result`
    },
    {
      id: "load",
      name: "ConfiguredDocumentLoader.load()",
      fileId: "loaders",
      summary: "문서 종류에 맞는 전용 로더를 골라 LoadedDocument 목록을 만듭니다.",
      how: "접수된 파일의 종류를 보고 PDF 창구와 상담 기록 창구 중 하나로 보내는 분기입니다. D3는 상담 한 건씩, PDF는 파일 하나를 문서 하나로 읽습니다.",
      terms: ["LoadedDocument", "PDF", "D3", "디스패치"],
      lines: [
        { at: "if source.doc_key == \"D3\":", text: "상담 이력이면 레코드별 로더로 보냅니다." },
        { at: "if Path(source.path).suffix.lower() == \".pdf\":", text: "PDF이면 페이지 텍스트와 좌표를 읽는 로더로 보냅니다." },
        { at: "raise ValueError(f\"지원하지 않는 원천 형식", text: "알 수 없는 형식을 조용히 넘기지 않고 즉시 오류로 알립니다." }
      ],
      code: `    def load(self, source: SourceRef) -> list[LoadedDocument]:
        \"\"\"원천 형식에 맞춰 원문 좌표와 정제 예정 구간을 가진 문서를 만듦.

        반환값: PDF는 파일당 한 문서, D3 상담 파일은 상담 레코드당 한 문서의 목록임.
        예외: 지원하지 않는 파일 형식, 텍스트 없는 PDF, 잘못된 상담 형식이면 ValueError를 발생시킴.
        부수효과: 원천 파일을 읽지만 변경하지 않음.
        \"\"\"

        if source.doc_key == \"D3\":
            return self._load_consultations(source)
        if Path(source.path).suffix.lower() == \".pdf\":
            return [self._load_pdf(source)]
        raise ValueError(f\"지원하지 않는 원천 형식입니다: {Path(source.path).suffix}\")`
    },
    {
      id: "split",
      name: "RecursiveDocumentSplitter.split()",
      fileId: "splitter",
      summary: "문서별 경계를 먼저 존중하면서 모든 청크를 토큰 상한 안으로 나눕니다.",
      how: "긴 글을 무작정 같은 글자 수로 자르지 않고, 조항·문장·줄처럼 자연스러운 이음새부터 찾습니다. 그래도 800토큰을 넘는 조각만 실제 토큰 수로 다시 자릅니다.",
      terms: ["재귀 분할", "정규식", "토큰", "중첩", "원문 좌표", "strict zip"],
      lines: [
        { at: "separators = tuple(self._policies.get", text: "D1·D2·D3 문서마다 다른 경계 순서를 가져옵니다." },
        { at: "chunk_size=policy.chunk_size", text: "길이 기준을 글자 수가 아닌 주입된 토큰 계산기로 적용합니다." },
        { at: "keep_separator=\"start\"", text: "조항 번호나 화자 표시 같은 경계 문자를 다음 청크 앞에 남깁니다." },
        { at: "aligned = self._align_pieces", text: "분할된 글이 원문의 어느 문자 구간인지 다시 맞춥니다." },
        { at: "ranges.extend(self._strict_ranges", text: "상한을 넘은 예외 조각만 실제 토큰 수로 더 잘게 자릅니다." },
        { at: "raise ValueError(\"청크가 토큰 상한", text: "마지막 검사에서도 800토큰을 넘으면 저장 단계로 보내지 않습니다." }
      ],
      code: `    def split(self, document: LoadedDocument, policy: SplitPolicy) -> list[RawChunk]:
        \"\"\"문서별 경계를 우선해 원문을 토큰 상한 안의 청크로 분할함.

        방법: 정규식 구분자로 재귀 분할한 뒤 원문 좌표를 복원하고, 상한 초과 조각을 실제 토큰 수로 재분할함.
        인자: policy 크기와 중첩은 토큰 단위임. 구분자 끝에 빈 문자열을 보충해 문자 단위 분할을 허용함.
        반환값: 원문 좌표와 순번을 보존한 청크 목록임.
        예외: 캡처 그룹이 있거나 원문 좌표를 복원할 수 없거나 토큰 상한을 지킬 수 없으면 ValueError를 발생시킴.
        부수효과: 최초 호출 시 LangChain 분할 모듈과 TokenCounterPort의 토크나이저를 불러와 캐시할 수 있음.
        \"\"\"

        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError as error:  # pragma: no cover - 선택 의존성 누락을 명확히 알리는 경로임
            raise RuntimeError(\"langchain-text-splitters 패키지가 필요합니다.\") from error

        separators = tuple(self._policies.get(document.doc_key, {}).get(\"separators\", policy.separators))
        if not separators or separators[-1] != \"\":
            separators = (*separators, \"\")
        for separator in separators[:-1]:
            if re.compile(separator).groups:
                raise ValueError(\"분할 정규식에는 캡처 그룹을 사용할 수 없습니다.\")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=policy.chunk_size,
            chunk_overlap=policy.chunk_overlap,
            length_function=self._counter.count,
            separators=list(separators),
            is_separator_regex=True,
            keep_separator=\"start\",
            add_start_index=True,
            strip_whitespace=False,
        )
        pieces = splitter.split_documents([Document(page_content=document.text)])
        ranges: list[tuple[int, int]] = []
        aligned = self._align_pieces(document.text, [piece.page_content for piece in pieces])
        for piece, (start, end) in zip(pieces, aligned, strict=True):
            if self._counter.count(piece.page_content) <= policy.chunk_size:
                ranges.append((start, end))
            else:
                ranges.extend(self._strict_ranges(document.text, start, end, policy))

        chunks = [
            RawChunk(document, document.text[start:end], start, end, ordinal)
            for ordinal, (start, end) in enumerate(ranges)
            if start < end
        ]
        if any(self._counter.count(chunk.text) > policy.chunk_size for chunk in chunks):
            raise ValueError(\"청크가 토큰 상한을 초과했습니다.\")
        return chunks`
    },
    {
      id: "load_split_clean",
      name: "IndexingWorkflow.load_split_clean()",
      fileId: "workflow",
      summary: "한 함수 안에서 실제 순서대로 문서를 로드하고, 청킹하고, 정제합니다.",
      how: "이 함수가 다섯 단계 가운데 앞 세 단계를 이어 주는 핵심입니다. 개인정보가 남은 원문은 메모리에서만 다루고, 외부 산출물에는 정제가 끝난 청크만 저장합니다.",
      terms: ["활성 세대", "부분 인덱싱", "체크포인트", "아티팩트", "dry run", "해시 재사용"],
      lines: [
        { at: "current_sources = self.sources.discover", text: "처리 직전에 원천을 다시 찾아 실행 시작 뒤 파일이 바뀌지 않았는지 확인합니다." },
        { at: "for document in self.loader.load(source):", text: "선택한 원천을 메모리 문서로 읽습니다. 이것이 로드입니다." },
        { at: "for raw_chunk in self.splitter.split(document, policy):", text: "로드한 문서를 정책에 따라 나눕니다. 이것이 청킹입니다." },
        { at: "processed_chunk = self.processor.process(raw_chunk)", text: "나눈 청크에서 불필요한 구간과 개인정보를 처리합니다. 이것이 정제입니다." },
        { at: "if processed_chunk.token_count > self.token_counter.max_tokens", text: "정제 후 다시 토큰 상한을 확인하여 모델에 너무 긴 입력이 가지 않게 합니다." },
        { at: "reference = self.artifacts.save(", text: "개인정보 처리가 끝난 청크만 재개 가능한 외부 산출물로 저장합니다." }
      ],
      code: `    def load_split_clean(self, state: IndexerState) -> dict[str, Any]:
        \"\"\"원문을 메모리에서 로드·분할·정제·개인정보 처리한 뒤 안전한 청크만 저장함.

        목적: 개인정보 처리 전 원문이 체크포인트나 중간 파일에 남지 않게 하기 위함.
        인자: state에는 발견 단계가 확정한 원천 목록과 지문이 있어야 함.
        반환값: 정제 완료 청크의 산출물 참조·건수와 실행 상태를 담은 상태 갱신값임.
        예외: 실행 중 원천 변경, 토큰 상한 초과, 청크 ID 중복 시 IndexingError를 발생시킴.
        부수효과: 원천 파일을 읽고 개인정보 처리가 끝난 청크만 외부 산출물 저장소에 기록함.
        \"\"\"

        request = state[\"request\"]
        partial = str(request.get(\"doc\", \"all\")) != \"all\" or request.get(\"segment\") is not None
        current_sources = self.sources.discover(
            str(request[\"input_path\"]),
            str(request.get(\"doc\", \"all\")),
            request.get(\"segment\"),
        )
        current_inputs = {source.source: source.sha256 for source in current_sources}
        expected_inputs = {
            source: digest
            for source, digest in state[\"inputs_sha256\"].items()
            if _selected_source(
                request,
                source,
                str(state.get(\"source_doc_keys\", {}).get(source, \"\")),
            )
        }
        if current_inputs != expected_inputs:
            # 발견 뒤 바뀐 파일을 처리하면 체크포인트의 지문과 실제 게시 내용이 달라져 재개가 안전하지 않음.
            raise IndexingError(
                \"원천 문서가 실행 시작 후 변경되었습니다. 현재 thread_id를 폐기하고 새 실행을 시작해야 합니다.\"
            )
        active = self.repository.load_active()
        active_chunks = list(active.chunks) if active else []
        old_inputs = dict(active.manifest.get(\"inputs_sha256\", {})) if active else {}
        policy_unchanged = bool(
            active
            and active.manifest.get(\"policy_signature\") == self.policy_signature
            and active.manifest.get(\"profile_signature\") == self.profile_signature
        )
        selected_sources = [_source_from_dict(row) for row in state[\"sources\"]]
        prepared: list[PreparedChunk] = []

        if active and partial:
            # 부분 실행은 선택 범위만 교체하므로 나머지 활성 청크를 새 세대에 그대로 포함함.
            prepared.extend(
                chunk
                for chunk in active_chunks
                if not _selected_source(
                    request,
                    str(chunk.metadata.get(\"source\", \"\")),
                    str(chunk.metadata.get(\"doc_key\", \"\")),
                )
            )

        active_by_source: dict[str, list[PreparedChunk]] = {}
        for chunk in active_chunks:
            active_by_source.setdefault(str(chunk.metadata.get(\"source\", \"\")), []).append(chunk)

        for source in selected_sources:
            if (
                not bool(request.get(\"full_reindex\"))
                and policy_unchanged
                and old_inputs.get(source.source) == source.sha256
                and source.source in active_by_source
            ):
                # 원천과 정제 계약이 같으면 개인정보 처리 완료 청크를 재사용해 원문 재처리를 피함.
                prepared.extend(active_by_source[source.source])
                continue
            for document in self.loader.load(source):
                policy = self.policies.get(document.doc_key, self.default_policy)
                document_chunks: list[PreparedChunk] = []
                for raw_chunk in self.splitter.split(document, policy):
                    processed_chunk = self.processor.process(raw_chunk)
                    if processed_chunk is None:
                        continue
                    if processed_chunk.token_count > self.token_counter.max_tokens:
                        raise IndexingError(
                            f\"임베딩 입력 한도를 초과한 청크입니다: {processed_chunk.chunk_id} \"
                            f\"({processed_chunk.token_count}>{self.token_counter.max_tokens})\"
                        )
                    document_chunks.append(processed_chunk)
                prepared.extend(self._finalize_document_chunks(document_chunks))

        by_id: dict[str, PreparedChunk] = {}
        for chunk in prepared:
            if chunk.chunk_id in by_id:
                raise IndexingError(f\"청크 ID가 중복되었습니다: {chunk.chunk_id}\")
            by_id[chunk.chunk_id] = chunk
        ordered = [by_id[key] for key in sorted(by_id)]
        reference = self.artifacts.save(
            state[\"run_id\"],
            \"prepared-chunks\",
            [_chunk_to_dict(chunk) for chunk in ordered],
        )
        return {
            \"prepared_chunks_ref\": reference,
            \"prepared_count\": len(ordered),
            \"status\": \"dry_run\" if request.get(\"dry_run\") else \"ok\",
            \"exit_code\": 0,
        }`
    },
    {
      id: "clean_chunk_text",
      name: "clean_chunk_text()",
      fileId: "text_rules",
      summary: "원문 좌표를 이용해 제외 구간을 지우고 본문의 개인정보를 삭제 표시나 연령대로 바꿉니다.",
      how: "종이 원본 위에 미리 표시한 삭제선과 가림표를 청크 범위에만 적용하는 과정입니다. 회원·상담사 가명 ID는 로더가 메타데이터에 따로 만들며, 이 함수는 본문 치환만 맡습니다.",
      terms: ["원문 좌표", "TextSpan", "개인정보", "가명 처리", "정규식"],
      lines: [
        { at: "for keep_start, keep_end in _kept_ranges(", text: "청크 안에서 보존할 원문 구간만 차례로 찾습니다." },
        { at: "_replace_private(", text: "보존 구간과 겹치는 개인정보를 [삭제] 또는 연령대처럼 미리 정한 값으로 바꿉니다." },
        { at: "cleaned = _SPACE_BEFORE_NEWLINE", text: "줄바꿈 앞에 남은 불필요한 공백을 정리합니다." },
        { at: "return _EXCESS_NEWLINES", text: "연속 빈 줄을 줄이고 앞뒤 공백을 제거한 문자열을 돌려줍니다." }
      ],
      code: `def clean_chunk_text(chunk: RawChunk) -> str:
    \"\"\"원문 좌표를 기준으로 제외 구간을 지운 뒤 남은 개인정보 구간을 치환함.

    목적: 먼저 문자열을 삭제하여 좌표가 바뀌거나 개인정보가 청크 경계에서 나뉘어 남는 일을 방지함.
    방법: 원문에서 남길 구간을 정하고 각 구간과 겹치는 개인정보를 치환한 뒤 공백을 정리함.
    반환값: 저장 후보 문자열임. 내용이 모두 제거되면 빈 문자열이며 잔존 검사와 토큰 검사는 별도로 필요함.
    부수효과: 없음. 원문 객체와 구간 목록을 변경하지 않음.
    \"\"\"

    pieces: list[str] = []
    for keep_start, keep_end in _kept_ranges(
        chunk.start, chunk.end, chunk.document.removal_spans
    ):
        pieces.append(
            _replace_private(
                chunk.document.text,
                keep_start,
                keep_end,
                chunk.document.privacy_spans,
            )
        )
    cleaned = \"\".join(pieces)
    cleaned = _SPACE_BEFORE_NEWLINE.sub(\"\\n\", cleaned)
    return _EXCESS_NEWLINES.sub(\"\\n\\n\", cleaned).strip()`
    },
    {
      id: "process",
      name: "ValidatingChunkProcessor.process()",
      fileId: "processor",
      summary: "정제한 청크가 안전하고 계약에 맞는지 확인한 뒤 PreparedChunk로 만듭니다.",
      how: "세척만 끝난 재료를 바로 포장하지 않고, 이물질·무게·라벨을 한 번 더 검사하는 단계입니다. 검사를 통과한 청크만 임베딩으로 갑니다.",
      terms: ["PreparedChunk", "메타데이터", "메타데이터 스키마", "본문 해시", "청크 ID", "토크나이저 서명"],
      lines: [
        { at: "text = clean_chunk_text(chunk)", text: "제외·치환 규칙을 적용하여 저장 후보 본문을 만듭니다." },
        { at: "assert_no_residual_private(text)", text: "전화번호나 이메일 같은 개인정보 형식이 남았는지 검사합니다." },
        { at: "token_count = self._counter.count(text)", text: "임베딩 모델과 같은 토크나이저로 실제 길이를 셉니다." },
        { at: "metadata = chunk_metadata", text: "출처·문서 유형·페이지 같은 검색용 설명표를 만듭니다." },
        { at: "text_hash = sha256_text(text)", text: "같은 본문인지 비교하여 벡터를 재사용할 수 있는 지문을 만듭니다." },
        { at: "return PreparedChunk(", text: "검사를 통과한 본문과 메타데이터를 다음 단계의 표준 묶음으로 반환합니다." }
      ],
      code: `    def process(self, chunk: RawChunk) -> PreparedChunk | None:
        \"\"\"원문 좌표의 제거·치환 규칙을 적용한 뒤 저장 가능한 청크를 만듦.

        목적: 머리말·꼬리말과 개인정보가 벡터DB나 BM25 corpus에 기록되는 것을 방지함.
        방법: 정제와 잔존 개인정보 검사 후 토큰 상한·메타데이터 스키마를 검증함.
        반환값: 정제 결과가 비면 None, 저장 가능하면 해시와 안정 ID를 포함한 청크임.
        예외: 개인정보가 남거나 토큰 상한·메타데이터 계약을 위반하면 ValueError를 발생시킴.
        부수효과: 없음.
        \"\"\"

        text = clean_chunk_text(chunk)
        if not text:
            return None
        assert_no_residual_private(text)
        token_count = self._counter.count(text)
        if token_count > self._counter.max_tokens:
            raise ValueError(\"정제된 청크가 임베딩 모델 입력 상한을 초과했습니다.\")

        metadata = chunk_metadata(chunk.document, chunk.start, chunk.end)
        required = tuple(self._schema[\"required\"])
        if any(not metadata.get(key) for key in required):
            raise ValueError(\"필수 메타데이터가 누락되었습니다.\")
        metadata.update(
            {
                \"pseudonymized\": bool(chunk.document.privacy_spans),
                \"chunk_index\": chunk.ordinal,
                \"char_start\": chunk.start,
                \"char_end\": chunk.end,
                \"char_len\": len(text),
                \"token_count\": token_count,
                \"tokenizer_signature\": self._counter.signature,
            }
        )
        text_hash = sha256_text(text)
        document_key = re.sub(r\"[^A-Za-z0-9_-]+\", \"_\", chunk.document.document_id).strip(\"_\")
        # 같은 본문이 반복되는 경우의 순번 접미사는 문서 전체를 보는 application 단계에서 붙임.
        chunk_id = f\"{document_key}_{text_hash[:16]}\"
        metadata[\"chunk_id\"] = chunk_id
        self._validate_metadata(metadata)
        return PreparedChunk(
            chunk_id=chunk_id,
            text=text,
            metadata=metadata,
            token_count=token_count,
            text_hash=text_hash,
            metadata_hash=stable_json_hash(metadata),
        )`
    },
    {
      id: "workflow_embed",
      name: "IndexingWorkflow.embed()",
      fileId: "workflow",
      summary: "아직 벡터가 없는 청크를 배치로 골라 임베더에 보내고 진행 위치를 기록합니다.",
      how: "할 일 목록에서 이번 묶음만 꺼내 처리하고 책갈피를 다음 위치로 옮기는 과정입니다. 중간 벡터를 별도 산출물에 저장하므로 체크포인트에는 큰 숫자 배열을 넣지 않습니다.",
      terms: ["배치", "커서", "아티팩트", "임베딩"],
      lines: [
        { at: "batch_ids = ids[cursor : cursor + self.embed_batch_size]", text: "현재 위치부터 설정한 배치 크기만큼 청크 ID를 꺼냅니다." },
        { at: "vectors = self.embedder.embed", text: "청크 본문 목록을 실제 임베더에 보내 숫자 벡터를 받습니다." },
        { at: "if len(vectors) != len(batch_ids)", text: "입력 청크 수와 결과 벡터 수가 같은지 확인합니다." },
        { at: "f\"vectors-{cursor:08d}\"", text: "재개할 때 찾을 수 있도록 현재 위치가 들어간 이름으로 벡터 묶음을 저장합니다." }
      ],
      code: `    def embed(self, state: IndexerState) -> dict[str, Any]:
        \"\"\"계획의 다음 청크 묶음을 임베딩하고 벡터 참조와 커서를 갱신함.

        인자: state에는 임베딩 대상 ID, 정제 청크 참조, 현재 커서가 있어야 함.
        반환값: 누적 벡터 산출물 참조와 다음 임베딩 커서를 담은 상태 갱신값임.
        예외: 임베딩 결과 수가 입력 수와 다르면 IndexingError를 발생시킴.
        부수효과: 모델 추론을 수행하고 새 벡터 묶음을 외부 산출물 저장소에 기록함.
        \"\"\"

        chunks = {chunk.chunk_id: chunk for chunk in self._load_chunks(state)}
        ids = list(state[\"plan\"][\"embed_ids\"])
        cursor = int(state.get(\"embed_cursor\", 0))
        batch_ids = ids[cursor : cursor + self.embed_batch_size]
        if not batch_ids:
            return {\"embed_cursor\": len(ids)}
        vectors = self.embedder.embed([chunks[chunk_id].text for chunk_id in batch_ids])
        if len(vectors) != len(batch_ids):
            raise IndexingError(\"임베딩 결과 수가 입력 청크 수와 다릅니다.\")
        reference = self.artifacts.save(
            state[\"run_id\"],
            f\"vectors-{cursor:08d}\",
            dict(zip(batch_ids, vectors, strict=True)),
        )
        return {
            \"vector_refs\": [*state.get(\"vector_refs\", []), reference],
            \"embed_cursor\": cursor + len(batch_ids),
        }`
    },
    {
      id: "embed_texts",
      name: "HuggingFaceEmbedder.embed()",
      fileId: "embedder",
      summary: "청크 본문을 모델로 보내고 길이가 일정한 단위 벡터 목록으로 바꿉니다.",
      how: "문장을 지도 위의 좌표로 옮긴다고 생각하면 됩니다. 뜻이 비슷한 문장은 가까운 좌표를 갖도록 모델이 숫자를 만들고, 코드는 비교 기준이 흔들리지 않게 벡터 길이를 1로 맞춥니다.",
      terms: ["Hugging Face", "SentenceTransformer", "벡터", "벡터 차원", "L2 정규화", "유한수"],
      lines: [
        { at: "if any(not isinstance(text, str)", text: "빈 문자열이나 문자열이 아닌 입력을 모델에 보내지 않습니다." },
        { at: "values = self._load().encode(", text: "고정한 모델 revision으로 청크 본문을 벡터로 변환합니다." },
        { at: "normalize_embeddings=True,", text: "모델에도 벡터 길이를 1로 맞추도록 요청합니다." },
        { at: "if len(row) != expected", text: "모든 결과가 약속한 차원이고 정상 숫자인지 확인합니다." },
        { at: "normalized = [float(value) / norm", text: "저장 직전 다시 계산하여 작은 반올림 오차까지 바로잡습니다." }
      ],
      code: `    def embed(self, texts: list[str]) -> list[list[float]]:
        \"\"\"비어 있지 않은 문자열 배치를 길이 1의 단일 벡터로 변환함.

        방법: 모델 정규화를 적용한 뒤 저장 직전 float 값으로 L2 정규화를 다시 검증함.
        반환값: 입력 순서를 유지하며 L2 노름이 1인 모델 출력 차원의 벡터 목록임.
        예외: 빈 입력 문자열, 행 수·차원 불일치, 유한하지 않은 값이나 0 노름이면 ValueError를 발생시킴.
        부수효과: 최초 호출 시 모델 파일을 읽고 메모리에 유지함. local_files_only가 False이면 다운로드할 수 있음.
        \"\"\"

        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError(\"임베딩 입력은 비어 있지 않은 문자열이어야 합니다.\")
        values = self._load().encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        rows = values.tolist() if hasattr(values, \"tolist\") else [list(row) for row in values]
        if len(rows) != len(texts):
            raise ValueError(\"임베딩 입력과 출력 행 수가 일치하지 않습니다.\")
        expected = self.dimension
        normalized_rows: list[list[float]] = []
        for row in rows:
            if len(row) != expected or any(not math.isfinite(float(value)) for value in row):
                raise ValueError(\"임베딩 출력 차원 또는 숫자 값이 올바르지 않습니다.\")
            norm = math.sqrt(sum(float(value) ** 2 for value in row))
            if not math.isfinite(norm) or norm <= 0:
                raise ValueError(\"임베딩 출력의 L2 노름이 올바르지 않습니다.\")
            # KURE-v2의 단일 벡터 변환은 normalize_embeddings=True에서도 저정밀도 반올림으로
            # 실제 노름이 약 0.997 ~ 1.003이 될 수 있어 저장 직전에 float 값으로 다시 정규화함.
            normalized = [float(value) / norm for value in row]
            checked_norm = math.sqrt(sum(value * value for value in normalized))
            if not math.isclose(checked_norm, 1.0, rel_tol=1e-6, abs_tol=1e-6):
                raise ValueError(\"임베딩 출력을 L2 정규화할 수 없습니다.\")
            normalized_rows.append(normalized)
        return normalized_rows`
    },
    {
      id: "workflow_upsert",
      name: "IndexingWorkflow.upsert()",
      fileId: "workflow",
      summary: "전체 대상 가운데 다음 적재 묶음을 골라 저장소에 넘기고 진행 위치를 갱신합니다.",
      how: "완성된 상자를 한꺼번에 창고로 밀어 넣지 않고 64개씩 운반하며 체크합니다. 실패해도 마지막 완료 위치부터 이어갈 수 있습니다.",
      terms: ["upsert", "배치", "커서", "비활성 세대"],
      lines: [
        { at: "batch_ids = desired_ids[cursor : cursor + self.upsert_batch_size]", text: "최종 청크 순서에서 이번에 저장할 ID만 꺼냅니다." },
        { at: "missing = [chunk_id for chunk_id in batch_ids", text: "청크에 대응하는 벡터가 모두 준비되었는지 확인합니다." },
        { at: "self.repository.upsert(", text: "청크와 벡터를 같은 순서로 저장소에 넘깁니다." },
        { at: "\"completed_ids\": [*state.get", text: "이번에 끝난 ID를 누적하여 재개 상태를 갱신합니다." }
      ],
      code: `    def upsert(self, state: IndexerState) -> dict[str, Any]:
        \"\"\"최종 청크 순서의 다음 묶음을 대상 색인 세대에 적재함.

        인자: state에는 전체 대상 ID, 모든 벡터 참조, 현재 적재 커서가 있어야 함.
        반환값: 다음 적재 커서와 누적 완료 청크 ID를 담은 상태 갱신값임.
        예외: 필요한 벡터가 없으면 IndexingError를 발생시키고 저장소 쓰기 예외는 그대로 전달함.
        부수효과: 활성 세대와 분리된 대상 세대의 벡터 저장소를 갱신함.
        \"\"\"

        chunks = {chunk.chunk_id: chunk for chunk in self._load_chunks(state)}
        desired_ids = list(state[\"plan\"][\"desired_ids\"])
        cursor = int(state.get(\"upsert_cursor\", 0))
        batch_ids = desired_ids[cursor : cursor + self.upsert_batch_size]
        if not batch_ids:
            return {\"upsert_cursor\": len(desired_ids)}
        vectors = self._load_vectors(state)
        missing = [chunk_id for chunk_id in batch_ids if chunk_id not in vectors]
        if missing:
            raise IndexingError(f\"적재할 벡터가 없습니다: {', '.join(missing)}\")
        self.repository.upsert(
            state[\"target_generation\"],
            [chunks[chunk_id] for chunk_id in batch_ids],
            [vectors[chunk_id] for chunk_id in batch_ids],
        )
        return {
            \"upsert_cursor\": cursor + len(batch_ids),
            \"completed_ids\": [*state.get(\"completed_ids\", []), *batch_ids],
        }`
    },
    {
      id: "repository_begin",
      name: "GenerationIndexRepository.begin()",
      fileId: "repository",
      summary: "현재 검색 중인 인덱스를 건드리지 않고 새 저장 세대를 준비합니다.",
      how: "영업 중인 매장을 닫고 공사하지 않고, 옆 공간에 새 매장을 완성한 뒤 나중에 입구 표지만 바꾸는 방식입니다. 이 함수는 옆 공간을 준비하는 부분입니다.",
      terms: ["세대", "활성 세대", "임베딩 서명", "Chroma 컬렉션"],
      lines: [
        { at: "generation_dir = self._generation_dir(generation)", text: "새 세대만의 안전한 디렉터리 경로를 정합니다." },
        { at: "if str(state.get(\"embedding_signature\"))", text: "같은 세대 이름을 다른 임베딩 규칙으로 재사용하지 못하게 합니다." },
        { at: "\"status\": \"building\"", text: "아직 검색에 공개하지 않은 구축 중 상태로 기록합니다." },
        { at: "self._open(generation, embedding_signature)", text: "새 세대의 Chroma 컬렉션을 열거나 만듭니다." }
      ],
      code: `    def begin(self, generation: str, embedding_signature: str) -> None:
        \"\"\"활성 세대를 건드리지 않고 새 세대의 Chroma 준비 상태를 만듦.

        인자: generation은 영문·숫자로 시작하는 128자 이하 안전 이름이어야 함.
        예외: 같은 세대를 다른 임베딩 서명으로 재사용하면 ValueError를 발생시킴.
        부수효과: 새 세대 디렉터리·상태 파일·Chroma 컬렉션을 생성함.
        \"\"\"

        generation_dir = self._generation_dir(generation)
        state_path = generation_dir / \"generation_state.json\"
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding=\"utf-8-sig\"))
            if str(state.get(\"embedding_signature\")) != embedding_signature:
                raise ValueError(\"같은 generation을 다른 임베딩 서명으로 재사용할 수 없습니다.\")
        else:
            # 디렉터리 생성 직후 프로세스가 종료되어도 같은 세대 재시도가 상태 파일을 복구할 수 있어야 함.
            generation_dir.mkdir(parents=True, exist_ok=True)
            _replace_json(
                state_path,
                {
                    \"generation\": generation,
                    \"embedding_signature\": embedding_signature,
                    \"collection\": self.collection,
                    \"base_generation\": (self._active_pointer() or {}).get(\"generation\"),
                    \"status\": \"building\",
                },
            )
        self._open(generation, embedding_signature)`
    },
    {
      id: "repository_upsert",
      name: "GenerationIndexRepository.upsert()",
      fileId: "repository",
      summary: "검증한 청크·벡터·메타데이터를 같은 ID로 Chroma 컬렉션에 저장합니다.",
      how: "청크 본문은 상품 설명, 벡터는 위치 좌표, 메타데이터는 분류표와 같습니다. 같은 청크 ID가 다시 오면 새 내용으로 갱신되므로 중단 뒤 재시도해도 중복 행을 만들지 않습니다.",
      terms: ["upsert", "Chroma", "컬렉션", "벡터 차원", "메타데이터", "유한수"],
      lines: [
        { at: "if len(chunks) != len(vectors)", text: "청크마다 벡터 하나가 있는지 먼저 확인합니다." },
        { at: "if len(set(ids)) != len(ids)", text: "한 배치 안에서 같은 청크 ID가 두 번 나오지 않게 막습니다." },
        { at: "dimensions = {len(vector) for vector in vectors}", text: "모든 벡터의 숫자 개수가 같은지 검사합니다." },
        { at: "collection.upsert(", text: "ID·본문·벡터·메타데이터를 같은 순서로 Chroma에 보냅니다." },
        { at: "metadatas=[_clean_metadata", text: "Chroma가 저장할 수 있는 단순 값만 남긴 메타데이터를 저장합니다." }
      ],
      code: `    def upsert(
        self,
        generation: str,
        chunks: list[PreparedChunk],
        vectors: list[list[float]],
    ) -> None:
        \"\"\"검증한 청크·벡터 배치를 아직 활성화되지 않은 세대에 저장함.

        인자: 청크와 벡터 행 수가 같고 ID가 중복되지 않으며 벡터 차원이 일정해야 함.
        예외: 입력 계약 위반 시 ValueError를, Chroma 저장 실패 시 어댑터 예외를 발생시킴.
        부수효과: 해당 세대의 Chroma 컬렉션을 변경함. 활성 포인터는 변경하지 않음.
        \"\"\"

        if len(chunks) != len(vectors):
            raise ValueError(\"청크 수와 벡터 수가 일치하지 않습니다.\")
        if not chunks:
            return
        ids = [chunk.chunk_id for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError(\"한 배치에 중복 chunk_id가 있습니다.\")
        dimensions = {len(vector) for vector in vectors}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError(\"벡터 차원이 일정하지 않습니다.\")
        if any(not math.isfinite(float(value)) for vector in vectors for value in vector):
            raise ValueError(\"벡터에 유한하지 않은 값이 있습니다.\")
        collection = self._open(generation)
        collection.upsert(
            ids=ids,
            documents=[chunk.text for chunk in chunks],
            embeddings=vectors,
            metadatas=[_clean_metadata(chunk.metadata, chunk.chunk_id) for chunk in chunks],
        )`
    }
  ],
  glossary: {
    "진입점": "프로그램 실행이 처음 들어오는 위치입니다. 이 예제에서는 run_indexer.py입니다.",
    "종료 코드": "프로그램이 성공했는지 실패했는지 운영체제와 자동화 도구에 알려 주는 숫자입니다.",
    "__name__": "파이썬이 현재 파일을 직접 실행했는지, 다른 파일이 가져왔는지 구분할 때 쓰는 특별한 값입니다.",
    "CLI": "명령행 인터페이스입니다. 화면의 버튼 대신 --input 같은 글자 옵션으로 프로그램을 조작합니다.",
    "IndexRequest": "입력 경로, 문서 종류, 실행 ID 같은 한 번의 인덱싱 요청 값을 묶은 객체입니다.",
    "thread_id": "중단된 실행을 같은 체크포인트부터 이어 가기 위한 실행 식별자입니다.",
    "지연 import": "필요한 순간까지 모듈 가져오기를 미루는 방식입니다. 도움말만 볼 때 무거운 모델 관련 코드를 읽지 않게 합니다.",
    "의존성 주입": "객체가 필요한 도구를 안에서 직접 고르지 않고 바깥에서 받아 쓰는 구성 방식입니다.",
    "포트": "응용 코드가 로더나 저장소에 요구하는 동작의 약속입니다. 실제 기술을 바꿔도 흐름을 유지하게 합니다.",
    "토크나이저": "문장을 모델이 읽는 작은 단위인 토큰으로 나누고 번호로 바꾸는 도구입니다.",
    "Chroma": "청크 본문, 임베딩 벡터, 메타데이터를 함께 보관하고 벡터 유사도 검색을 지원하는 저장소입니다.",
    "BM25": "질문과 문서에 같은 중요 단어가 얼마나 나타나는지 계산하는 키워드 검색 방식입니다.",
    "LangGraph": "여러 처리 단계를 상태와 함께 연결하고 체크포인트·재시도를 관리하는 실행 도구입니다.",
    "토큰": "모델이 문장을 읽을 때 나누는 작은 단위입니다. 한 글자나 한 단어와 항상 일치하지 않습니다.",
    "특수 토큰": "문장의 시작·끝처럼 모델이 입력 구조를 알아보도록 자동으로 덧붙이는 토큰입니다.",
    "청크": "긴 문서를 검색과 임베딩이 다루기 좋은 크기로 나눈 한 조각입니다.",
    "중첩": "청크 경계에서 문맥이 끊기지 않도록 앞 청크의 끝부분을 다음 청크에 일부 다시 넣는 방식입니다.",
    "구분자": "문서를 자르기 좋은 경계를 나타내는 문자나 규칙입니다. 조항 시작, 문장 끝, 줄바꿈 등이 해당합니다.",
    "데이터클래스": "값을 담는 객체를 간결하게 정의하도록 파이썬이 생성자와 비교 기능을 만들어 주는 문법입니다.",
    "SHA-256": "파일 내용으로 만드는 긴 디지털 지문입니다. 내용이 달라지면 지문도 달라집니다.",
    "SourceRef": "원천 파일의 경로, 이름, 문서 종류, SHA-256을 한 묶음으로 보관하는 데이터입니다.",
    "심볼릭 링크": "실제 파일 대신 다른 위치를 가리키는 링크입니다. 입력 범위를 벗어날 수 있어 이 코드에서는 제외합니다.",
    "문서 정책": "D1·D2·D3별 파일명 규칙, 접근 수준, 청킹 경계를 모아 둔 설정입니다.",
    "LoadedDocument": "원문과 출처 정보, 제거·개인정보·문맥 구간의 좌표를 함께 담은 메모리 문서입니다.",
    "PDF": "페이지와 글자 배치 정보를 담는 문서 형식입니다. 이 코드는 PyMuPDF의 텍스트 계층을 읽습니다.",
    "D3": "교육용 합성 상담 이력 문서 유형입니다. 상담 레코드별로 나누고 제한 접근 메타데이터를 붙입니다.",
    "디스패치": "입력 종류를 보고 알맞은 담당 함수로 보내는 분기입니다.",
    "재귀 분할": "큰 조각이면 다음 경계 규칙을 사용해 다시 나누는 과정을 반복하는 방식입니다.",
    "정규식": "전화번호나 조항 시작처럼 일정한 문자열 모양을 찾는 규칙 표현입니다.",
    "원문 좌표": "원문 문자열에서 시작 문자 위치와 끝 문자 위치를 숫자로 표시한 범위입니다.",
    "strict zip": "두 목록을 짝지을 때 길이가 다르면 조용히 버리지 않고 오류를 내는 파이썬 옵션입니다.",
    "활성 세대": "현재 검색 서비스가 실제로 읽고 있는 검증 완료 인덱스 묶음입니다.",
    "부분 인덱싱": "D1 같은 일부 문서만 새로 처리하고 선택하지 않은 기존 청크는 유지하는 실행입니다.",
    "체크포인트": "중단 뒤 이어 갈 수 있도록 단계와 진행 위치를 저장한 기록입니다.",
    "아티팩트": "정제 청크나 벡터처럼 크기가 커서 체크포인트 밖에 별도 저장하고 참조로 연결하는 중간 결과입니다.",
    "dry run": "로드·청킹·정제·검증까지만 수행하고 실제 인덱스를 게시하지 않는 시험 실행입니다.",
    "해시 재사용": "본문 지문이 같으면 이미 만든 벡터를 다시 사용해 모델 계산을 줄이는 방식입니다.",
    "TextSpan": "원문의 시작·끝 문자 위치와 그 구간에 적용할 값을 함께 담은 데이터입니다.",
    "개인정보": "전화번호, 이메일, 회원번호처럼 개인을 알아볼 수 있어 저장 전에 제거하거나 바꿔야 하는 정보입니다.",
    "가명 처리": "회원·상담사 식별자를 원래 값 대신 안정적인 가명 ID로 바꾸는 처리입니다. 본문의 전화번호·이메일 삭제나 생년월일의 연령대 일반화와는 구분합니다.",
    "PreparedChunk": "정제와 검사를 통과한 본문, 메타데이터, 토큰 수, 해시를 묶은 저장 준비 청크입니다.",
    "메타데이터": "청크의 출처, 문서 종류, 페이지, 접근 수준처럼 검색 필터와 결과 설명에 쓰는 부가 정보입니다.",
    "메타데이터 스키마": "필수 키, 허용 키, 가능한 값을 정해 메타데이터 모양을 검사하는 계약입니다.",
    "본문 해시": "정제된 본문으로 만든 SHA-256 지문입니다. 같은 본문의 기존 벡터를 찾는 데 사용합니다.",
    "청크 ID": "청크를 저장하고 다시 찾기 위한 고유 이름입니다. 문서 ID와 본문 해시를 바탕으로 만듭니다.",
    "토크나이저 서명": "어떤 모델과 규칙으로 토큰 수를 셌는지 나타내는 식별값입니다.",
    "배치": "여러 청크를 한 번의 모델 호출이나 저장 요청으로 묶은 단위입니다.",
    "커서": "전체 목록에서 어디까지 처리했는지 나타내는 위치입니다.",
    "임베딩": "글의 의미를 비교할 수 있도록 고정 길이 숫자 벡터로 바꾸는 과정입니다.",
    "Hugging Face": "모델과 모델 파일을 배포하고 불러오는 생태계입니다. 이 코드는 고정 revision을 사용합니다.",
    "SentenceTransformer": "문장이나 문서 전체를 하나의 의미 벡터로 바꾸는 라이브러리입니다.",
    "벡터": "청크의 의미를 나타내는 숫자 목록입니다. 서로 가까운 벡터는 의미도 비슷하다고 판단합니다.",
    "벡터 차원": "벡터에 들어 있는 숫자의 개수입니다. 보관된 감사 결과의 실제 값은 768입니다.",
    "L2 정규화": "벡터의 길이가 1이 되도록 모든 값을 같은 비율로 나누는 처리입니다.",
    "유한수": "무한대나 숫자가 아님을 뜻하는 NaN이 아닌, 저장하고 계산할 수 있는 정상 숫자입니다.",
    "upsert": "같은 ID가 없으면 새로 넣고, 이미 있으면 그 ID의 값을 갱신하는 저장 동작입니다.",
    "비활성 세대": "아직 검색 서비스에 공개하지 않고 구축·검증 중인 새 인덱스 묶음입니다.",
    "세대": "벡터 인덱스와 BM25 인덱스를 같은 시점의 한 묶음으로 식별하는 버전입니다.",
    "임베딩 서명": "모델과 프롬프트 정책 등 벡터 생성 규칙을 구분하는 문자열입니다.",
    "Chroma 컬렉션": "Chroma 안에서 같은 종류의 청크와 벡터를 모아 두는 논리적 묶음입니다.",
    "컬렉션": "저장소 안에서 같은 목적의 레코드를 함께 관리하는 묶음입니다."
  }
};
