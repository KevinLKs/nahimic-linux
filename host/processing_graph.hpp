#pragma once

class ProcessingGraph {
    struct Stage {
        ApoConfiguration* configuration=nullptr;
        ApoRealtime* realtime=nullptr;
        Connection input{},output{};
        bool locked=false;
    };
    std::vector<Stage> stages_;
    std::vector<std::vector<float>> buffers_;
    FloatMediaType* format_=nullptr;
    FloatMediaType* application_format_=nullptr;
    size_t block_=0;
public:
    static constexpr UINT32 frames=256,channels=2;
    ProcessingGraph()=default;
    ProcessingGraph(const ProcessingGraph&)=delete;
    ProcessingGraph& operator=(const ProcessingGraph&)=delete;
    ~ProcessingGraph(){close();}
    bool open(const std::vector<AudioProcessingObject*>& apos,const wchar_t* application_path=nullptr,DWORD application_pid=0){
        if(apos.empty() || !stages_.empty())return false;
        IID configuration_id{},realtime_id{};
        if(FAILED(CLSIDFromString(L"{0E5ED805-ABA6-49C3-8F9A-2B8C889C4FA8}",&configuration_id)) ||
           FAILED(CLSIDFromString(L"{9E1D6A6D-DDBC-4E95-A4C7-AD64BA37846C}",&realtime_id)))return false;
        stages_.resize(apos.size());
        buffers_.resize(apos.size()+1,std::vector<float>(frames*channels));
        format_=new FloatMediaType(48000,channels,3);
        if(application_path){
            application_format_=new FloatMediaType(48000,channels,3);
            if(!application_format_->set_application(application_path,application_pid))return false;
        }
        for(size_t i=0;i<apos.size();++i){
            std::fprintf(stderr,"graph_stage=%zu\n",i);
            auto& stage=stages_[i];auto apo=apos[i];
            HRESULT hr=apo->QueryInterface(configuration_id,reinterpret_cast<void**>(&stage.configuration));
            status("QueryConfiguration",hr);if(FAILED(hr))return false;
            hr=apo->QueryInterface(realtime_id,reinterpret_cast<void**>(&stage.realtime));
            status("QueryRealtime",hr);if(FAILED(hr))return false;
            IAudioMediaType* suggested=nullptr;
            auto input_format=(i==0 && application_format_)?application_format_:format_;
            hr=apo->IsInputFormatSupported(format_,input_format,&suggested);status("InputFormat48000StereoFloat",hr);
            if(suggested)suggested->Release();
            if(hr!=S_OK)return false;
            suggested=nullptr;
            hr=apo->IsOutputFormatSupported(input_format,format_,&suggested);status("OutputFormat48000StereoFloat",hr);
            if(suggested)suggested->Release();
            if(hr!=S_OK)return false;
            stage.input={1,reinterpret_cast<UINT_PTR>(buffers_[i].data()),frames,input_format,0x41434453};
            stage.output={1,reinterpret_cast<UINT_PTR>(buffers_[i+1].data()),frames,format_,0x41434453};
            auto pin=&stage.input;auto pout=&stage.output;
            hr=stage.configuration->LockForProcess(1,&pin,1,&pout);status("LockForProcess",hr);
            if(FAILED(hr))return false;
            stage.locked=true;
            INT64 latency=0;hr=apo->GetLatency(&latency);status("GetLatency",hr);
            if(FAILED(hr))return false;
            std::fprintf(stderr,"stage=%zu declared_latency_100ns=%lld\n",i,latency);
        }
        return true;
    }
    bool process(const float* input,float* output){
        if(stages_.empty())return false;
        std::copy_n(input,frames*channels,buffers_.front().data());
        auto flags=BUFFER_VALID;
        for(size_t i=0;i<stages_.size();++i){
            auto& stage=stages_[i];auto& samples=buffers_[i+1];
            if(!stage.locked)return false;
            std::fill(samples.begin(),samples.end(),NAN);
            APO_CONNECTION_PROPERTY in{stage.input.buffer,frames,flags,0x41435053};
            APO_CONNECTION_PROPERTY out{stage.output.buffer,0,BUFFER_INVALID,0x41435053};
            auto pin=&in;auto pout=&out;
            stage.realtime->APOProcess(1,&pin,1,&pout);
            if(out.u32ValidFrameCount!=frames || (out.u32BufferFlags!=BUFFER_VALID && out.u32BufferFlags!=BUFFER_SILENT)){
                std::fprintf(stderr,"Invalid output stage=%zu block=%zu frames=%u flags=%u\n",i,block_,out.u32ValidFrameCount,out.u32BufferFlags);return false;
            }
            flags=out.u32BufferFlags;
            if(flags==BUFFER_SILENT)std::fill(samples.begin(),samples.end(),0.0f);
            for(float x:samples)if(!std::isfinite(x)){
                std::fprintf(stderr,"Nonfinite output stage=%zu block=%zu\n",i,block_);return false;
            }
        }
        std::copy_n(buffers_.back().data(),frames*channels,output);++block_;return true;
    }
    bool close(){
        bool valid=true;
        for(auto it=stages_.rbegin();it!=stages_.rend();++it){
            if(it->locked){
                HRESULT hr=it->configuration->UnlockForProcess();status("UnlockForProcess",hr);
                if(FAILED(hr))valid=false;
                it->locked=false;
            }
            if(it->realtime)it->realtime->Release();
            if(it->configuration)it->configuration->Release();
        }
        stages_.clear();buffers_.clear();
        if(format_)format_->Release();
        format_=nullptr;
        if(application_format_)application_format_->Release();
        application_format_=nullptr;
        return valid;
    }
};
